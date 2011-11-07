import functools
import httplib
import os
import tornado.web

import router
import util
from db import D
from handlers.base import BaseHandler
from handlers import *


@router.route(r"/")
class RootHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        if self.current_user["type"] == "contestant":
            self.redirect("/contestant")
        elif self.current_user["type"] == "admin":
            self.redirect("/admin")
        else:
            self.send_error(403)


@router.route(r"/login")
class LoginHandler(BaseHandler):
    def get(self):
        return self.render("login.html")

    def post(self):
        username = self.get_argument("username", "")
        password = self.get_argument("password", "")
        user = D.users.find_one({ "username": username })
        if user and util.hashed_eq(password, user["password"]):
            self.set_secure_cookie("user_id", str(user["_id"]))
            self.redirect("/")
        else:
            return self.render(
                "login.html",
                errors=[("Invalid login.",
                         "Please check your login data carefully and try again.")]
            )


@router.route(r"/logout")
class LogoutHandler(BaseHandler):
    def get(self):
        self.set_secure_cookie("user_id", "")
        self.redirect("/")


@router.route(r".*", priority=1)
class NotFoundHandler(BaseHandler):
    def get(self):
        return self.handle();

    def post(self):
        return self.handle();

    def handle(self):
        return self.render("404.html")


ROOT_DIR = os.path.dirname(__file__)

settings = {
    "cookie_secret": "3bQ0YcnGfW1wjP7BRLtpVkiggf4dNByRpcdy7xR7re9VPbiODURsMP8Vt7Zy",
    "xsrf_cookies": True,
    "debug": True,
    "login_url": "/login",
    "static_path": os.path.join(ROOT_DIR, "static"),
    "template_path": os.path.join(ROOT_DIR, "tmpl"),
}

if __name__ == "__main__":
    application = tornado.web.Application(router.get_routes(), **settings)
    application.listen(8888)

    from tornado.ioloop import IOLoop
    tornado.ioloop.IOLoop.instance().start()
