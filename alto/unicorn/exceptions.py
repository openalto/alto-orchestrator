class UnknownEventType(Exception):
    def __init__(self, event_type):
        self.message = "Unknown Event type %s" % event_type


class UnknownIP(Exception):
    def __init__(self, ip):
        self.message = "Unknown IP %s" % ip
