import base
import itertools
import router
import util

from bson.objectid import ObjectId
from db import D, ProblemsFS


class AdminBaseHandler(base.BaseHandler):
    @util.authenticated_as("admin")
    def prepare(self):
        pass


@router.route(r"/admin")
class AdminRootHandler(AdminBaseHandler):
    def get(self):
        self.render(
            "admin/root.html",
            admin=self.current_user
        )


@router.route(r"/admin/contestants")
class AdminContestansHandler(AdminBaseHandler):
    def get(self):
        contestants = D.users.find({"type": "contestant"})
        self.render(
            "admin/contestants.html",
            admin=self.current_user,
            contestants=contestants
        )

    def post(self):
        username = self.get_argument("username", "")
        password = util.hashed_pw(self.get_argument("password", ""))
        type_ = self.get_argument("type", "")
        D.users.insert({"username": username, "password": password, "type": type_})
        self.write("Ajax.reload()")


@router.route(r"/admin/contestants/([a-f0-9]+)/delete")
class AdminContestantsDeleteHandler(AdminBaseHandler):
    def post(self, id_):
        D.users.remove({"_id": ObjectId(id_)})
        self.write("Ajax.reload()")


@router.route(r"/admin/problems")
class AdminProblemsHandler(AdminBaseHandler):
    def get(self):
        problems = D.problems.find()
        self.render(
            "admin/problems.html",
            admin=self.current_user,
            problems=problems
        )

    def post(self):
        name = self.get_argument("name", "")
        try: time_limit = float(self.get_argument("time_limit", "0"))
        except ValueError: time_limit = 0.0
        try: input_id = ProblemsFS.put(self.request.files["input"][0]["body"])
        except KeyError: input_id = ProblemsFS.put("")
        try: output_id = ProblemsFS.put(self.request.files["output"][0]["body"])
        except KeyError: output_id = ProblemsFS.put("")
        D.problems.insert({
            "name": name,
            "input": input_id,
            "output": output_id,
            "time_limit": time_limit,
        })
        self.redirect("/admin/problems")


@router.route(r"/admin/problems/([a-f0-9]+)/(input|output)")
class AdminProblemsFileHandler(AdminBaseHandler):
    def get(self, id_, type_):
        file_id = D.problems.find_one({"_id": ObjectId(id_)})[type_]
        print file_id
        self.set_header("Content-Type", "text/plain")
        with ProblemsFS.get(file_id) as fh:
            self.write(fh.read())


@router.route(r"/admin/problems/([a-f0-9]+)/delete")
class AdminProblemsDeleteHandler(AdminBaseHandler):
    def post(self, id_):
        problem = D.problems.find_one({"_id": ObjectId(id_)})
        try: ProblemsFS.delete(problem["input"])
        except KeyError: pass
        try: ProblemsFS.delete(problem["output"])
        except KeyError: pass
        D.problems.remove({"_id": problem["_id"]})
        self.write("Ajax.reload()")


@router.route(r"/admin/problems/gc")
class AdminProblemsGCHandler(AdminBaseHandler):
    def post(self):
        file_ids = frozenset(itertools.chain(
            *[ [problem["input"], problem["output"]] for problem in D.problems.find() ]
        ))
        [ ProblemsFS.delete(fl["_id"])
          for fl in D.problems.fs.files.find()
          if fl["_id"] not in file_ids ]
