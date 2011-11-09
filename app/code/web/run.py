import json
import zmq, zmq.eventloop, zmq.eventloop.zmqstream
from bson.objectid import ObjectId

from db import ProblemsFS


class ProblemFileReplier(object):
    __instance = None

    @classmethod
    def get(cls):
        if not cls.__instance:
            cls.__instance = ProblemFileReplier()
        return cls.__instance

    def setup(self, socket):
        self._stream = zmq.eventloop.zmqstream.ZMQStream(socket, zmq.eventloop.IOLoop.instance())
        self._stream.on_recv(self.handle)

    def handle(self, msg):
        with ProblemsFS.get(ObjectId(msg[0])) as fh:
            self._stream.send(fh.read())


class JudgingRequester(object):
    __instance = None

    @classmethod
    def get(cls):
        if not cls.__instance:
            cls.__instance = JudgingRequester()
        return cls.__instance

    def setup(self, socket):
        self._stream = zmq.eventloop.zmqstream.ZMQStream(socket, zmq.eventloop.IOLoop.instance())

    def submit(self, problem, callback):
        def on_recv(msg):
            self._stream.stop_on_recv()
            callback(json.loads(msg[0]))
        def on_send(*_):
            self._stream.on_recv(on_recv)
        self._stream.send(json.dumps(problem), callback=on_send)


def setup():
    context = zmq.Context()

    socket = context.socket(zmq.REP)
    socket.bind("tcp://127.0.0.1:10301")
    ProblemFileReplier.get().setup(socket)

    socket = context.socket(zmq.REQ)
    socket.bind("tcp://127.0.0.1:10302")
    JudgingRequester.get().setup(socket)
