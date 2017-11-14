from alto.unicorn.entries import RegisterEntry, TasksEntry, TasksLookupEntry, ResourcesLookupEntry


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

    def add_route(self, url, obj, config=None):
        if isinstance(obj, type):
            if config:
                obj = obj(**config)
            else:
                obj = obj()
        self.obj_map[url] = obj

    def rm_route(self, url):
        self.obj_map.pop(url)


routes = Routes()


def set_route(app, config=None):
    # Add your routes here
    routes.add_route("/register", RegisterEntry, config)
    routes.add_route("/task", TasksEntry)
    routes.add_route("/tasks_lookup", TasksLookupEntry)
    routes.add_route("/resources_lookup", ResourcesLookupEntry)

    for i in routes:
        app.add_route(i, routes[i])
