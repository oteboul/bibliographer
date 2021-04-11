"""Show the found bibliography."""

import tornado.web
from bibliographer import aggregator


class MainHandler(tornado.web.RequestHandler):

    def initialize(self):
        self.config = self.application.config
        self.db = self.application.db
        self._aggregator = aggregator.CitationAggregator(self.db)
        origins = [
            v for v in self.db.values() if v is not None and v.depth == 1]
        self.origin = origins[0] if len(origins) == 1 else None

    def get(self):
        articles = self._aggregator.most_cited(50)
        self.render("index.html",
                    total=len(self._aggregator),
                    origin=self.origin,
                    articles=articles,
                    config=self.config)