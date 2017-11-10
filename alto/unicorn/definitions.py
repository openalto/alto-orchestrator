class Definitions():
    class QueryType():
        PATH_QUERY_TYPE = "path-query"
        RESOURCE_QUERY_TYPE = "resource-query"

    class QueryAction():
        ADD = "add"
        DELETE = "delete"
        MERGE = "merge"
        ERASE = "erase"
        NEW = "new"

    class EventType():
        UPDATE_STREAM = "application/updatestreamcontrol"
        JSON = "application/json"

    MAX_WAITING_FLOWS = 10
    POLL_TIME = 0.5
    WAIT_TIME_AFTER_REG = 2
