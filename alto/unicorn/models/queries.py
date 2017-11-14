from threading import Lock

from alto.unicorn.models.flows import FlowDataProvider
from alto.unicorn.models.singleton import SingletonType


class QueryItem(object):
    def __init__(self, flow_id, ingress_point):
        # Generate query item id
        self._id = QueryItem._gen_id()

        # Add to all items
        QueryItem._id_items[self._id] = self

        self._flow_id = flow_id
        self._ingress_point = ingress_point

    # Next generated id
    _next_id = 1

    # All items
    _id_items = dict()  # type: dict[str, QueryItem]

    @staticmethod
    def get(query_item_id):
        return QueryItem._id_items[query_item_id]

    @staticmethod
    def _gen_id():
        QueryItem._next_id += 1
        return QueryItem._next_id - 1

    @property
    def flow_id(self):
        return self._flow_id

    @property
    def ingress_point(self):
        return self._ingress_point

    @property
    def flow(self):
        return FlowDataProvider().get(self._flow_id)

    def to_dict(self):
        result = dict()
        result["flow"] = self.flow.to_dict()
        result["ingress-point"] = self.ingress_point
        return result


class DomainQuery(object):
    def __init__(self, query_id, domain_name):
        self.query_id = query_id
        self._domain_name = domain_name

        # Flow id -> query item
        self._query_items = dict()  # type: dict[int, QueryItem]
        self._response = ""

    @property
    def domain_name(self):
        return self._domain_name

    @property
    def query_items(self):
        """
        :rtype: list[QueryItem]
        """
        return list(self._query_items.values())

    @property
    def response(self):
        """
        :rtype: str
        """
        return self._response

    @response.setter
    def response(self, response):
        self._response = response

    def add_query_item(self, query_item):
        """
        :type query_item: QueryItem
        """
        self._query_items[query_item.flow_id] = query_item

    def get_query_item(self, flow_id):
        return self._query_items[flow_id]

    def to_list(self):
        return [item.to_dict() for item in self._query_items.values()]

class Query(object):
    def __init__(self, query_id):
        self._query_id = query_id  # type: int
        self._query_type = ""  # type: str
        self._domain_query = dict()  # type: dict[str, DomainQuery]
        self._lock = Lock()

    @property
    def query_id(self):
        return self._query_id

    @property
    def query_type(self):
        return self._query_type

    @property
    def domain_query(self):
        return self._domain_query

    @query_type.setter
    def query_type(self, query_type):
        with self._lock:
            self._query_type = query_type

    @domain_query.setter
    def domain_query(self, domain_query):
        with self._lock:
            self._domain_query = domain_query

    @property
    def domain_queries(self):
        return self._domain_query.values()

    def add(self, domain_query):
        """
        :type domain_query: DomainQuery
        """
        with self._lock:
            self._domain_query[domain_query.domain_name] = domain_query

    def get_domain_query(self, domain_name):
        """
        :rtype: DomainQuery
        """
        if domain_name not in self._domain_query:
            self._domain_query[domain_name] = DomainQuery(self._query_id, domain_name)
        return self._domain_query[domain_name]


class QueryDataProvider(metaclass=SingletonType):
    """
    Basic Idea: path query_id -> query object
    """

    def __init__(self):
        super(QueryDataProvider, self).__init__()

        # Query id -> Query Object
        self._queries = dict()

        self._next_id = 1

        self._lock = Lock()

    def gen_query_id(self):
        """
        Generate a query id and add it to data store
        :rtype: int
        """
        self._add_query_id(self._next_id)
        with self._lock:
            self._next_id += 1
        return self._next_id - 1

    def _add_query_id(self, query_id):
        """
        :type query_id: int
        """
        with self._lock:
            query = Query(query_id)
            self._queries[query_id] = query

    def get(self, query_id=None):
        """
        :type query_id: int
        :rtype: Query
        """
        if query_id is not None:
            if type(query_id) != "int":
                query_id = int(query_id)
            return self._queries[query_id]
        raise KeyError
