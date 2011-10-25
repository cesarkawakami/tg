import os
from bson.objectid import ObjectId
import tornado.ioloop
import tornado.web

ROOT_DIR = os.path.dirname(__file__)

class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return False# data.users.find_one(ObjectId(self.get_secure_cookie("user_id")))

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")

class LoginHandler(BaseHandler):
    def get(self):
        return self.render("login.html")

settings = {
    "template_path": os.path.join(ROOT_DIR, "tmpl"),
    "static_path": os.path.join(ROOT_DIR, "static"),
    "cookie_secret": "3bQ0YcnGfW1wjP7BRLtpVkiggf4dNByRpcdy7xR7re9VPbiODURsMP8Vt7Zy",
    "debug": True,
}

routes = [
    (r"/", MainHandler),
    (r"/login", LoginHandler),
]

if __name__ == "__main__":
    application = tornado.web.Application(routes, **settings)
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
