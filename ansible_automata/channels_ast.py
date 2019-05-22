
from collections import namedtuple

AST = namedtuple('AST', ['channels'])
Channel = namedtuple('Channel', ['name', 'from_fsm', 'from_queue', 'to_fsm', 'to_connector'])
