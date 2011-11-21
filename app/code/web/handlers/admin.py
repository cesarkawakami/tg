import base
import itertools
from bson.objectid import ObjectId

import web.router
import web.util
from web.db import D, ProblemsFS



class AdminBaseHandler(base.BaseHandler):
    @web.util.authenticated_as("admin")
    def prepare(self):
        pass


@web.router.route(r"/admin")
class AdminRootHandler(AdminBaseHandler):
    def get(self):
        self.render(
            "admin/root.html",
            user=self.current_user
        )


@web.router.route(r"/admin/users")
class AdminUsersHandler(AdminBaseHandler):
    def get(self):
        admins = D.users.find({"type": "admin"})
        contestants = D.users.find({"type": "contestant"})
        self.render(
            "admin/users.html",
            user=self.current_user,
            admins=admins,
            contestants=contestants
        )

    def post(self):
        username = self.get_argument("username", "")
        password = util.hashed_pw(self.get_argument("password", ""))
        type_ = self.get_argument("type", "")
        D.users.insert({"username": username, "password": password, "type": type_})
        self.write("Ajax.reload()")


@web.router.route(r"/admin/users/([a-f0-9]+)/delete")
class AdminUsersDeleteHandler(AdminBaseHandler):
    def post(self, id_):
        D.users.remove({"_id": ObjectId(id_)})
        self.write("Ajax.reload()")


@web.router.route(r"/admin/problems")
class AdminProblemsHandler(AdminBaseHandler):
    def get(self):
        problems = D.problems.find()
        files = [
            {
                "id": fl["_id"],
                "size": fl["length"],
                "references": " ".join(( p["name"] for p in itertools.chain(
                    D.problems.find({"output": fl["_id"]}),
                    D.problems.find({"input": fl["_id"]})
                ) )),
            }
            for fl in D.problems.fs.files.find()
        ]
        self.render(
            "admin/problems.html",
            user=self.current_user,
            problems=problems,
            files=files
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


@web.router.route(r"/admin/problems/([a-f0-9]+)/(input|output)")
class AdminProblemsFileHandler(AdminBaseHandler):
    def get(self, id_, type_):
        file_id = D.problems.find_one({"_id": ObjectId(id_)})[type_]
        self.set_header("Content-Type", "text/plain")
        with ProblemsFS.get(file_id) as fh:
            self.write(fh.read())


@web.router.route(r"/admin/problems/([a-f0-9]+)/delete")
class AdminProblemsDeleteHandler(AdminBaseHandler):
    def post(self, id_):
        problem = D.problems.find_one({"_id": ObjectId(id_)})
        try: ProblemsFS.delete(problem["input"])
        except KeyError: pass
        try: ProblemsFS.delete(problem["output"])
        except KeyError: pass
        D.problems.remove({"_id": problem["_id"]})
        self.write("Ajax.reload()")


@web.router.route(r"/admin/problems/files/([a-f0-9]+)/delete")
class AdminProblemsFilesDeleteHandler(AdminBaseHandler):
    def post(self, id_):
        ProblemsFS.delete(ObjectId(id_))
        self.write("Ajax.reload()")


@web.router.route(r"/admin/runs")
class AdminRunsHandler(AdminBaseHandler):
    def get(self):
        runs = D.runs.find()
        self.render(
            "admin/runs.html",
            user=self.current_user,
            runs=runs
        )


@web.router.route(r"/admin/runs/([a-f0-9]+)/delete")
class AdminRunsDeleteHandler(AdminBaseHandler):
    def post(self, id_):
        D.runs.remove(ObjectId(id_))
        self.write("Ajax.reload()")
