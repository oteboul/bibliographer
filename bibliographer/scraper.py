"""Keep scraping the references from pubmed."""

import logging
from typing import Optional, List
import shelve
import signal
import sys

from tornado import queues
import tornado.ioloop

from bibliographer import pmc
from bibliographer import pubmed
from bibliographer import citation


class BiblioScraper:
    """An async scraper."""

    def __init__(self,
                 filename: str,
                 seeds: Optional[List[str]] = None,
                 max_depth: int = 5):
        self.filename = filename
        self.db = shelve.open(filename)
        self.queue = queues.Queue()
        self.seeds = seeds
        self.max_depth = max_depth
        self.parsers = [pubmed.PubmedFetcher(), pmc.PMCFetcher()]
        self.initialize_queue()

        self._stop_request = False
        signals = set([signal.SIGQUIT, signal.SIGINT, signal.SIGTERM])
        for sig in signals:
            signal.signal(sig, self.stop)

    async def scrape(self):
        while not self.queue.empty() and not self._stop_request:
            depth, url = await self.queue.get()
            try:
                await self.process(depth, url)
            except:
                self.db.close()
                raise
            finally:
                self.queue.task_done()
            
        logging.info("Saving to db.")     
        self.db.close()

    def stop(self, *args):
        for parser in self.parsers:
            parser.stop()

        self._stop_request = True
        tornado.ioloop.IOLoop.current().stop()
        logging.info(f'Stopping {self.__class__.__name__} gracefully.')
        # sys.exit(1)

    def add_to_queue(self, depth: int, url: str):
        if url and url not in self.db:
            self.queue.put((depth, url))

    def add_citation_to_queue(self, cite: citation.Citation):
        for ref in cite.references + cite.cited_by:
            for url in (ref.pm_url, ref.pmc_url):
                self.add_to_queue(cite.depth, url)

    def initialize_queue(self):
        """Initializes the queue with the seeds or the unfound links."""
        if self.seeds:
            for seed in self.seeds:
                self.add_to_queue(0, seed)
            return

        for url in self.db.keys():
            self.add_citation_to_queue(self.db[url])

    async def process(self, depth, url):
        """Processes a single element from the queue."""
        if depth > self.max_depth:
            return
        
        if url in self.db:
            cite = self.db[url]
            cite.depth = min(cite.depth, depth + 1)
            self.db[url] = cite
            return

        matches = [p.matches(url) for p in self.parsers]
        if not any(matches):
            logging.error(f'No parser found for {url}')
            return

        parser = self.parsers[matches.index(True)]                
        html = await parser.fetch(url)
        if html is None:
            return

        # TODO(oliviert): add a try catch here.
        cite = parser.parse(html)
        cite.depth = depth + 1
        self.db[url] = cite
        self.add_citation_to_queue(cite)    