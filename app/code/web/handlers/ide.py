import tornado.web
import uuid
import web.router
import web.util
from web.db import D
from bson.objectid import ObjectId
from tornado import gen

import base
import web.comm


@web.router.route(r"/ide")
class IdeHandler(base.BaseHandler):
    def get(self):
        self.render(
            "ide/root.html"
        )


@web.router.route(r"/ide/run")
class IdeRunHandler(base.BaseHandler):
    @tornado.web.asynchronous
    @gen.engine
    def post(self):
        request_data = {
            "type": "ide",
            "source": self.get_argument("source", ""),
        }
        print "+++++++++++ INCOMING REQ +++++++++++++++"
        import traceback
        traceback.print_stack()
        print repr(self.request)
        result = yield gen.Task(web.comm.WorkerRequester.get().request, request_data)
        self.finish(result["result"])


class ContestantBaseHandler(base.BaseHandler):
    @web.util.authenticated_as("contestant")
    def prepare(self):
        pass


# @web.router.route(r"/contestant")
class ContestantRootHandler(ContestantBaseHandler):
    def get(self):
        self.render(
            "contestant/root.html",
            user=self.current_user
        )


# @web.router.route(r"/contestant/problems")
class ContestantProblemsHandler(ContestantBaseHandler):
    def get(self):
        problems = list(D.problems.find())
        self.render(
            "contestant/problems.html",
            user=self.current_user,
            problems=problems
        )

    @gen.engine
    def post(self):
        problem = D.problems.find_one({"_id": ObjectId(self.get_argument("problem", ""))})
        if not problem:
            raise HTTPError(400)
        run = {
            "user": self.current_user["_id"],
            "problem": problem["_id"],
            "language": self.get_argument("language", ""),
            "source": self.request.files["source"][0]["body"],
            "result": None,
        }
        D.runs.insert(run)
        self.redirect("/contestant/problems")
        request_data = {
            "id": str(run["_id"]),
            "type": "judge",
            "language": run["language"],
            "input": str(problem["input"]),
            "output": str(problem["output"]),
            "time_limit": problem["time_limit"],
            "source": run["source"],
        }
        result = yield gen.Task(web.comm.WorkerRequester.get().request, request_data)
        print result
        run["result"] = result
        D.runs.save(run)
        D.hashes.find_and_modify(
            {"object": "runs"},
            {"object": "runs", "hash": str(uuid.uuid4())}
        )
        web.comm.ContestantPublisher.get().publish({"msg": "update"}, str(self.current_user["_id"]))


# @web.router.route(r"/contestant/runs")
class ContestantRunsHandler(ContestantBaseHandler):
    def get(self):
        runs = [
            dict(run, problem_name=D.problems.find_one({"_id": run["problem"]})["name"])
            for run in D.runs.find(
                {"user": self.current_user["_id"]},
                sort=[("$natural", -1)],
                limit=5
            )
        ]
        self.render(
            "contestant/runs.html",
            runs=runs
        )


# @web.router.route(r"/contestant/channel/runs")
class ContestantChannelRunsHandler(ContestantBaseHandler):
    @tornado.web.asynchronous
    @gen.engine
    def post(self):
        self.__handled = False
        hash_ = self.get_argument("hash", "")
        self.subscriber = web.comm.ContestantSubscriber(str(self.current_user["_id"]), self.handle)
        yield gen.Task(self.subscriber.setup)
        current_hash = D.hashes.find_one({"object": "runs"})["hash"]
        if current_hash != hash_:
            self.__handled = True
            self.subscriber.close()
            self.finish({"hash": current_hash})

    def handle(self, data):
        if self.__handled:
            return
        self.finish({"hash": D.hashes.find_one({"object": "runs"})["hash"]})

    def on_connection_close(self):
        self.__handled = True
        self.subscriber.close()
