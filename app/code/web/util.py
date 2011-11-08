import functools
import hashlib
import random
import string

import tornado.web

def hashed_pw(password, salt=None):
    if salt is None:
        salt = "".join(( random.choice(string.ascii_letters + string.digits) for x in range(10) ))
    hasher = hashlib.md5()
    hasher.update(salt + password)
    return salt + "$" + hasher.hexdigest()

def hashed_eq(password, hsh):
    try:
        salt, _ = hsh.split("$")
        return hsh == hashed_pw(password, salt)
    except:
        return False

def authenticated_as(user_type):
    def deco(method):
        @tornado.web.authenticated
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            if self.current_user["type"] != user_type:
                self.send_error(403)
            else:
                return method(self, *args, **kwargs)
        return wrapper
    return deco
