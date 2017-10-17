from .registry import Registry


class Routes(object):
    def __init__(self):
        self.obj_map = dict()

    def __iter__(self):
        for i in self.obj_map.keys():
            yield i

    def __getitem__(self, item):
        return self.obj_map[item]

    def __contains__(self, item):
        return item in self.obj_map.keys()

    def addRoute(self, url, obj, config=None):
        if isinstance(obj, type):
            obj = obj(config)
        self.obj_map[url] = obj

    def rmRoute(self, url):
        self.obj_map.pop(url)


routes = Routes()


def set_route(app, config=None):
    # Add your routes here
    routes.addRoute("/register", Registry, config)

    for i in routes:
        app.add_route(i, routes[i])
