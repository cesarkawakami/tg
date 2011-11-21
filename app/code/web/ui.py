import tornado.web

ui_modules = {}

def ui_module(cls):
    ui_modules[cls.__name__] = cls
    return cls

class BaseUIModule(tornado.web.UIModule):
    def render(self):
        return ""

@ui_module
class ContestantHub(BaseUIModule):
    def javascript_files(self): return [
        "jquery.history.js",
        "channel-updater.js",
        "contestant-hub.js",
    ]
