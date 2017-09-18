#!/usr/bin/env python

import sys
import json
import argparse
import falcon
import gunicorn.app.base
from gunicorn.six import iteritems

def parse_argument():
    args = argparse.ArgumentParser(description='ALTO Orchestrator Service.')
    args.add_argument('-c', '--config', dest='config',
                      type=argparse.FileType('r'),
                      help='Specify the json format configuration file')
    args.add_argument('-a', '--address', dest='address',
                      default='127.0.0.1')
    args.add_argument('-p', '--port', dest='port',
                      default='6666', type=int,
                      help='TCP port the service will listen on (default: 6666).')
    args.add_argument('-v', '--verbose', action='store_true',
                      help='Enable verbosity to trace import statements')

class Registry(object):

    def __init__(self, config):
        pass

    def register(self, domain, base_url, **params):
        # Store the agent info into db
        pass

    def on_post(self, req, res):
        raw_data = req.stream.read()
        agent_info = json.loads(raw_data.decode('utf-8'))

        feedback = self.register(**agent_info)
        res.status = falcon.HTTP_200
        res.body = json.dumps(feedback)

class OrchestratorService(gunicorn.app.base.BaseApplication):

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super(OrchestratorService, self).__init__()

    def load_config(self):
        config = dict([(key, value) for key, value in iteritems(self.options)
                       if key in self.cfg.settings and value is not None])
        for key, value in iteritems(config):
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

if __name__ == '__main__':
    args = parse_argument()
    config = args.parse_args(sys.argv[1:])

    options = {
        'bind': '%s:%d' % (config.config.get('address', config.address),
                           config.config.get('port', config.port))
    }
    app = falcon.API()
    registry = Registry(config)
    app.add_route('/register', registry)
    OrchestratorService(app, options).run()
