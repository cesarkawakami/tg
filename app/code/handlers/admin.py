import router
import util

from base import BaseHandler
from bson.objectid import ObjectId
from db import D


@router.route(r"/admin")
class AdminRootHandler(BaseHandler):
    @util.authenticated_as("admin")
    def get(self):
        self.render(
            "admin-root.html",
            admin=self.current_user
        )


@router.route(r"/admin/contestants")
class AdminContestansHandler(BaseHandler):
    @util.authenticated_as("admin")
    def get(self):
        contestants = D.users.find({"type": "contestant"})
        self.render(
            "admin-contestants.html",
            admin=self.current_user,
            contestants=contestants
        )

@router.route(r"/admin/contestants/add")
class AdminContestansAddHandler(BaseHandler):
    @util.authenticated_as("admin")
    def post(self):
        username = self.get_argument("username", "")
        password = util.hashed_pw(self.get_argument("password", ""))
        type_ = self.get_argument("type", "")
        D.users.insert({"username": username, "password": password, "type": type_})
        self.write("Ajax.reload()")

@router.route(r"/admin/contestants/delete")
class AdminContestansDeleteHandler(BaseHandler):
    @util.authenticated_as("admin")
    def post(self):
        id_ = self.get_argument("id", "")
        D.users.remove({"_id": ObjectId(id_)})
        self.write("Ajax.reload()")
