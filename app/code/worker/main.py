import contextlib
import difflib
import json
import os
import pika, pika.adapters
import re
import resource
import signal
import subprocess
import uuid
from bson.objectid import ObjectId
from tornado import gen

import proto


ROOT_TMP_DIR = "/sandbox"
TMP_DIR = os.path.join(ROOT_TMP_DIR, "tmp")
BIN_DIR = os.path.join(ROOT_TMP_DIR, "bin")
BOX_DIR = os.path.join(ROOT_TMP_DIR, "box")


@proto.singleton
class WorkerReplier(proto.WorkerMixin, proto.Replier):
    def __init__(self):
        super(WorkerReplier, self).__init__()
        self._handlers = {}

    def set_handlers(self, handlers):
        self._handlers = handlers

    @gen.engine
    def handle(self, data, route_data):
        print "===== got request ====="
        try:
            handler_cls = self._handlers[data["type"]]
        except KeyError:
            print "rejecting", str(data)
            self.channel.basic_reject(requeue=True, **route_data["ack"])
            return
        handler = handler_cls()
        answer = yield gen.Task(handler.handle, data)
        print answer
        self.respond(answer, route_data)
        print "===== end request ====="


@proto.singleton
class ProblemFileRequester(proto.ProblemFileMixin, proto.Requester):
    def request(self, id_, callback):
        def clb(data):
            callback(self.decode(data["blob"]))
        super(ProblemFileRequester, self).request({"id": id_}, clb)


class FilePrintHandler(object):
    @gen.engine
    def handle(self, data, callback):
        blob = yield gen.Task(ProblemFileRequester.get().request, data["file_id"])
        print "length:", len(blob)
        import string
        print "first chars:", "".join([ ch for ch in blob[:40] if ch in string.printable ])
        callback({"status": "ok"})


class JudgeHandler(object):
    @contextlib.contextmanager
    def phase(self, desc=""):
        print "=== entering \"{0}\" ===".format(desc)
        yield
        print "=== done     \"{0}\" ===".format(desc)

    def prepare_process(self, cpu=None, memory=None):
        def delegate():
            if cpu:
                resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
            if memory:
                resource.setrlimit(resource.RLIMIT_DATA, (memory, memory))
            # hard limits on anything
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))
            # creating a process group to ease killing
            os.setsid()
        return delegate

    @gen.engine
    def handle(self, data, callback):
        with self.phase("downloading"):
            input_blob = yield gen.Task(ProblemFileRequester.get().request, data["input"])
            output_blob = yield gen.Task(ProblemFileRequester.get().request, data["output"])
            source_blob = data["source"]

        with self.phase("cleaning"):
            subprocess.call(["rm", "-rf", os.path.join(TMP_DIR, "*")])
            subprocess.call(["rm", "-rf", os.path.join(BIN_DIR, "*")])
            subprocess.call(["rm", "-rf", os.path.join(BOX_DIR, "*")])

        source_fn = os.path.join(TMP_DIR, "a.cpp")
        input_fn = os.path.join(TMP_DIR, "input")
        candidate_fn = os.path.join(TMP_DIR, "candidate")
        error_fn = os.path.join(TMP_DIR, "error")
        exec_fn = os.path.join(BIN_DIR, "a")

        with self.phase("initialization"):
            with open(source_fn, "w") as fh:
                fh.write(source_blob)
            with open(input_fn, "w") as fh:
                fh.write(input_blob)

        with self.phase("compilation"):
            p = subprocess.Popen(
                args=["g++", "-Wall", "-O2", "-static", "-o", exec_fn, source_fn],
                stdin=None,
                stdout=None,
                stderr=subprocess.PIPE,
                preexec_fn=self.prepare_process(cpu=10),
                close_fds=True
            )
            compilation_result = p.wait()
            if compilation_result != 0:
                callback({
                    "status": "compilation error",
                    "compilation_messages": p.stderr.read(),
                })
                return

        with self.phase("execution"):
            input_file = open(input_fn, "r")
            candidate_file = open(candidate_fn, "w")
            error_file = open(error_fn, "w")
            import pprint
            utime_before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime
            p = subprocess.Popen(
                args=[exec_fn],
                stdin=input_file,
                stdout=candidate_file,
                stderr=error_file,
                preexec_fn=self.prepare_process(int(data["time_limit"]) + 1),
                close_fds=True,
                env={}
            )
            execution_result = p.wait()
            # killing process group
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                pass
            # check time limit
            print "user time before execution:", utime_before
            utime_after = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime
            print "user time after execution:", utime_after
            exec_time = utime_after - utime_before
            if exec_time > data["time_limit"]:
                callback({"status": "time limit exceeded"})
                return
            # check correctness
            with open(candidate_fn, "r") as fh:
                candidate_blob = fh.read()
                candidate_blob = normalize_whitespace(candidate_blob)
                output_blob = normalize_whitespace(output_blob)
                print candidate_blob
                print output_blob
                if candidate_blob == output_blob:
                    callback({"status": "ok"})
                    return
            # check errors
            if execution_result < 0:
                signal_no = -execution_result
                signal_names = dict(
                    (k, v) for v, k in signal.__dict__.iteritems() if v.startswith('SIG')
                )
                callback({
                    "status": "runtime error",
                    "type": "signal",
                    "signal": signal_names[signal_no],
                })
                return
            if execution_result > 0:
                callback({
                    "status": "runtime error",
                    "type": "nonzero return code"
                })
                return
            # defaulting to wrong answer
            callback({
                "status": "wrong answer"
            })


class IdeHandler(object):
    @contextlib.contextmanager
    def phase(self, desc=""):
        print "=== entering \"{0}\" ===".format(desc)
        yield
        print "=== done     \"{0}\" ===".format(desc)

    def prepare_process(self, cpu=None):
        def delegate():
            if cpu:
                resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu+1))
            # hard limits on anything
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))
            # creating a process group to ease killing
            os.setsid()
        return delegate

    @gen.engine
    def handle(self, data, callback):
        with self.phase("cleaning"):
            subprocess.call(["rm", "-rf", os.path.join(TMP_DIR, "*")])
            subprocess.call(["rm", "-rf", os.path.join(BIN_DIR, "*")])
            subprocess.call(["rm", "-rf", os.path.join(BOX_DIR, "*")])

        source_fn = os.path.join(TMP_DIR, "a.cpp")
        output_fn = os.path.join(TMP_DIR, "output")
        error_fn = os.path.join(TMP_DIR, "error")
        exec_fn = os.path.join(BIN_DIR, "a")

        with self.phase("initialization"):
            with open(source_fn, "w") as fh:
                print data["source"]
                fh.write(data["source"].encode("utf-8"))

        with self.phase("compilation"):
            p = subprocess.Popen(
                args=["g++", "-Wall", "-O2", "-static", "-o", exec_fn, source_fn],
                stdin=None,
                stdout=None,
                stderr=subprocess.PIPE,
                preexec_fn=self.prepare_process(cpu=10),
                close_fds=True
            )
            compilation_result = p.wait()
            if compilation_result != 0:
                callback({
                    "result": "===== COMPILATION ERROR =====\n" + p.stderr.read(),
                })
                return

        with self.phase("execution"):
            output_file = open(output_fn, "w")
            error_file = open(error_fn, "w")
            import pprint
            utime_before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime
            p = subprocess.Popen(
                args=[exec_fn],
                stdin=None,
                stdout=output_file,
                stderr=error_file,
                preexec_fn=self.prepare_process(cpu=30),
                close_fds=True,
                env={},
                cwd=BOX_DIR
            )
            execution_result = p.wait()
            # killing process group
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                pass
            # check time limit
            print "user time before execution:", utime_before
            utime_after = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime
            print "user time after execution:", utime_after
            exec_time = utime_after - utime_before
            # check errors
            if execution_result < 0:
                signal_no = -execution_result
                signal_names = dict(
                    (k, v) for v, k in signal.__dict__.iteritems() if v.startswith('SIG')
                )
                callback({
                    "result": "===== RUNTIME ERROR =====\nsignal: {0}".format(signal_names[signal_no]),
                })
                return
            if execution_result > 0:
                callback({
                    "result": "===== RUNTIME ERROR =====\nnonzero return code: {0}".format(execution_result),
                })
                return
            # defaulting to wrong answer
            with open(output_fn, "r") as fh:
                callback({
                    "result": fh.read(),
                })


def normalize_whitespace(buf):
    if not hasattr(normalize_whitespace, "re"):
        normalize_whitespace.re = re.compile(r"\s+", re.DOTALL)
    return normalize_whitespace.re.sub(" ", buf).strip()


class MainWorker(object):
    def run(self):
        proto.PikaClient.get().setup(
            clients=[
                ProblemFileRequester.get(),
                WorkerReplier.get(),
            ],
            parameters=pika.ConnectionParameters(host="localhost")
        )
        WorkerReplier.get().set_handlers({
            "test": FilePrintHandler,
            "judge": JudgeHandler,
            "ide": IdeHandler,
        })
        proto.PikaClient.get().connect()
        proto.PikaClient.get().start()

