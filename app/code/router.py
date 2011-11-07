import functools

all_routes = []

def route(path, args={}, priority=0):
    def deco(method):
        global all_routes
        all_routes.append((priority, path, method, args))
        return method
    return deco

def add_route(path, handler, args={}, priority=0):
    global all_routes
    all_routes.append((priority, path, handler, args))

def get_routes():
    return [(path, handler, args) for _, path, handler, args in sorted(all_routes)]
