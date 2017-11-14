from alto.unicorn.entries import RegisterEntry, TasksEntry, TasksLookupEntry, ResourcesLookupEntry, \
    ManagementIPLookupEntry, TaskLookupEntry, ResourceQueryCompleteLookupEntry, PathCompleteLookupEntry, \
    ResourceLookupEntry, SchedulingCompleteLookupEntry, SchedulingResultLookupEntry


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
    routes.add_route("/register", RegisterEntry, config)  # POST
    routes.add_route("/task", TasksEntry)  # POST
    routes.add_route("/path_complete_lookup/{task_id}", PathCompleteLookupEntry)  # GET
    routes.add_route("/task_lookup/{task_id}", TaskLookupEntry)  # GET
    routes.add_route("/tasks_lookup", TasksLookupEntry)  # GET
    routes.add_route("/resource_complete_lookup/{task_id}", ResourceQueryCompleteLookupEntry)  # GET
    routes.add_route("/resource_lookup/{task_id}", ResourceLookupEntry)  # GET
    routes.add_route("/resources_lookup", ResourcesLookupEntry)  # GET
    routes.add_route("/scheduling_complete_lookup/{task_id}", SchedulingCompleteLookupEntry)  # GET
    routes.add_route("/scheduling_result_lookup/{task_id}", SchedulingResultLookupEntry)  # GET
    routes.add_route("/management_ip_lookup/{ip}", ManagementIPLookupEntry)  # GET

    for i in routes:
        app.add_route(i, routes[i])
