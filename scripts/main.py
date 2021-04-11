import argparse
import logging
import os
import tornado.ioloop

from bibliographer import scraper


def run():
    fmt = '%(asctime)s - %(filename)s:%(lineno)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=fmt, level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--db', type=str, default='biblio.db', help='The path to the db.')
    parser.add_argument(
        '--depth', type=int, default=3, help='Distance to the seeds')
    parser.add_argument(
        '--sync_every', type=int, default=20, help='When to sync the db.')
    parser.add_argument(
        '--seeds', type=str, default='resources/seeds.txt', help='Url seed file.')
    args = parser.parse_args()

    if os.path.exists(args.db):
        seeds = None
    else:
        with open(args.seeds) as fp:
            seeds = [line.strip() for line in fp.readlines()]
    scp = scraper.BiblioScraper(
        args.db, seeds=seeds, max_depth=args.depth, sync_every=args.sync_every)
    loop = tornado.ioloop.IOLoop.current()
    loop.add_callback(scp.scrape)
    loop.start()


if __name__ == '__main__':
    run()