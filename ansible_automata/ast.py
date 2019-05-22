
from collections import namedtuple

AST = namedtuple('AST', ['fsms'])
FSM = namedtuple('FSM', ['name', 'hosts', 'gather_facts', 'roles', 'states', 'outputs', 'import_from'])
State = namedtuple('State', ['name', 'handlers'])
Handler = namedtuple('Handler', ['name', 'body'])
