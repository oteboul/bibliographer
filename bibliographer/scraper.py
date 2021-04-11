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
                 max_depth: int = 5,
                 sync_every: int = 20):
        self.filename = filename
        self.db = shelve.open(filename)
        self.queue = queues.Queue()
        self.seeds = seeds
        self.max_depth = max_depth
        self.parsers = [pubmed.PubmedFetcher()]
        self.count = 0
        self.initialize_queue()
        self.sync_every = sync_every

        self._stop_request = False
        signals = set([signal.SIGQUIT, signal.SIGINT, signal.SIGTERM])
        for sig in signals:
            signal.signal(sig, self.stop)

    async def scrape(self):
        while not self.queue.empty() and not self._stop_request:
            depth, url = await self.queue.get()
            try:
                success = await self.process(depth, url)
                self.count += int(success)
                if self.count % self.sync_every == 0:
                    logging.info(f'Syncing shelve ({self.count})')
                    self.db.sync()
            except:
                logging.error(f'Cannot process {url}')
                self.db[url] = None
            finally:
                self.queue.task_done()
            
        self.stop()

    def stop(self, *args):
        logging.info("Saving to db.")     
        self.db.close()
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
            self.count += 1
            self.add_citation_to_queue(self.db[url])
        logging.info(f'Already {self.count} citation on shelve.')

    async def process(self, depth, url) -> bool:
        """Processes a single element from the queue."""
        if depth > self.max_depth:
            return False
        
        if url in self.db:
            cite = self.db[url]
            cite.depth = min(cite.depth, depth + 1)
            self.db[url] = cite
            return False

        matches = [p.matches(url) for p in self.parsers]
        if not any(matches):
            logging.error(f'No parser found for {url}')
            return False

        parser = self.parsers[matches.index(True)]                
        try:
            html = await parser.fetch(url)
        except:
            logging.error(f'Could not fetch {url}')
            html = None
        if html is None:
            return False

        # TODO(oliviert): add a try catch here.
        cite = parser.parse(html)
        cite.depth = depth + 1
        self.db[url] = cite
        self.add_citation_to_queue(cite)    
        return True