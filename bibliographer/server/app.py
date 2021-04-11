"""A webserver for the citations."""

import logging
import os
import shelve
import signal
import sys

import tornado.web
import tornado.ioloop
import yaml

from bibliographer.server import handler
from bibliographer.server import uimodules


def format_authors(handler, *args):
    result = []
    authors = args[0]
    for a in authors:
        curr = a.split(' ')
        try:
            result.append(' '.join([c[0] + '.' for c in curr[:-1]] + curr[-1:]))
        except:
            continue
    return ', '.join(result)


class WebApp(tornado.web.Application):
    """A web app for the bibliographer."""

    def __init__(self, config: str = 'config'):
        with open(f'resources/{config}.yaml') as fp:
            self.config = yaml.load(fp, Loader=yaml.FullLoader)

        db_path = self.config.get('db', None)
        if db_path is None:
            raise ValueError("Please provide a db in the config file.")
        self.db = shelve.open(db_path, writeback=True)

        handlers = [
            (r"/", handler.MainHandler)
        ]
        settings = dict(
            application_title = u"Bibliographer",
            template_path = os.path.join(os.path.dirname(__file__), "templates"),
            static_path = os.path.join(os.path.dirname(__file__), "static"),
            autoescape = None,
            ui_methods={'format_authors': format_authors},
            ui_modules=uimodules,
        )
        tornado.web.Application.__init__(self, handlers, **settings)

        signals = set([signal.SIGQUIT, signal.SIGINT, signal.SIGTERM])
        for sig in signals:
            signal.signal(sig, self.stop)

    def stop(self, *args):
        self.db.close()
        tornado.ioloop.IOLoop.current().stop()
        logging.info(f"Stopping {self.__class__.__name__} gracefully.")
        sys.exit(1)

    
def run(config: str):
    logging.getLogger().setLevel(logging.INFO)
    app = WebApp(config)
    port = app.config['port']
    app.listen(port)
    loop = tornado.ioloop.IOLoop.current()
    logging.info(f"Up and running on port {port}")
    loop.start()