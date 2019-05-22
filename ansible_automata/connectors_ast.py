
from collections import namedtuple

AST = namedtuple('AST', ['connectors'])
Connector = namedtuple('Connector', ['type', 'name', 'config'])
