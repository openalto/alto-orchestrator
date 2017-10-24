class UnknownEventType(Exception):
    def __init__(self, event_type):
        self.message = "Unknown Event type %s" % event_type
