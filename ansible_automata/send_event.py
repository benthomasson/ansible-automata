
"""
Usage:
    send_event [options] <fsm-id> <event-name> [<args>...]

Options:
    -h, --help        Show this page
    --debug           Show debug logging
    --verbose         Show verbose logging
    --wait            Wait for responses until keyboard interrupt
"""
import argparse
import logging
import sys

from .client import ZMQClientChannel
from .messages import Event

logger = logging.getLogger('send_event')


def cli_parser():

    parser = argparse.ArgumentParser(description='send an event to automata')

    parser.add_argument('<fsm-id>', dest='fsm_id')
    parser.add_argument('<event-name>', dest='event_name')
    parser.add_argument('--debug', dest='debug')
    parser.add_argument('--verbose', dest='verbose')
    parser.add_argument('--wait', dest='wait')

    return parser



def main(args=None):
    if args is None:
        args = sys.argv[1:]
    parser = cli_parser()
    parsed_args = parser.parse_args(args)
    if parsed_args.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif parsed_args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)


    client = ZMQClientChannel(listening=parsed_args.wait)
    args = dict()
    for arg in parsed_args.args:
        if "=" in arg:
            key, _, value = arg.partition('=')
            if key in args:
                raise Exception("Duplicate values for '{0}' in args".format(key))
            args[key] = value
        else:
            raise Exception("Args should contain '=' between key and value")
    client.send(Event("",
                      parsed_args.fsm_id,
                      parsed_args.event_name,
                      args))

    if parsed_args.wait:
        try:
            while True:
                print(client.receive())
        except KeyboardInterrupt:
            pass

    return 0


