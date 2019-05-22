

"""
Usage:
    ansible-automata run [options] <private_data_dir> [--automata=<a>]

Options:
    -h, --help       Show this page
    --debug          Show debug logging
    --verbose        Show verbose logging
    --automata=<a>   Automata file (YAML)
    --channels=<h>   Channels file (YAML)
    --connectors=<c> Connectors file (YAML)
    --inventory=<i>  Use a specific inventory
"""

from gevent import monkey
monkey.patch_all(thread=False) # noqa

import logging
FORMAT = "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s" # noqa
logging.basicConfig(filename='ansible_automata.log', level=logging.DEBUG, format=FORMAT)  # noqa

import logging
import sys
import argparse

from .automata import ansible_automata_run

logger = logging.getLogger('cli')


def cli_parser():

    parser = argparse.ArgumentParser(description='start ansible automata')

    parser.add_argument('command', choices=['run'])

    parser.add_argument('private_data_dir',
                        help='Base directory containing Runner metadata (project, inventory, etc')

    parser.add_argument('--automata', dest='automata')
    parser.add_argument('--channels', dest='channels')
    parser.add_argument('--connectors', dest='connectors')
    parser.add_argument('--inventory', dest='inventory')

    return parser


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    parser = cli_parser()
    parsed_args = parser.parse_args(args)

    if parsed_args.command == "run":
        return ansible_automata_run(parsed_args.private_data_dir,
                                    parsed_args.automata,
                                    parsed_args.inventory,
                                    parsed_args.channels,
                                    parsed_args.connectors)
