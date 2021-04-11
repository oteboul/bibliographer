"""Runs the debug server."""

import argparse

from bibliographer.server import app


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config', type=str, default='config',
        help='The name of the config to run.')
    args = parser.parse_args()
    app.run(args.config)