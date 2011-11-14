import tornado.web

from bson.objectid import ObjectId
from db import D

class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        try:
            return D.users.find_one({
                "_id": ObjectId(self.get_secure_cookie("user_id"))
            })
        except:
            return None

    # this works around a annoying bug in tornado that happens when the client closes the connection
    def finish(self, *args, **kwargs):
        try:
            super(BaseHandler, self).finish(*args, **kwargs)
        except IOError:
            pass
