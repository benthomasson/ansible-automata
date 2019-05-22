
from ansible_automata import ast
from ansible_automata import parser
import yaml
import os

HERE = os.path.abspath(os.path.dirname(__file__))


def load_test_fsm(name):
    with open(os.path.join(HERE, 'inputs', name)) as f:
        return yaml.safe_load(f.read())


def test_null():
    null_ast = parser.parse_to_ast(list())
    assert len(null_ast.fsms) == 0
    assert type(null_ast) == ast.AST


def test_single():
    data = load_test_fsm('single.yml')
    single_ast = parser.parse_to_ast(data)
    assert len(single_ast.fsms) == 1
    assert single_ast.fsms[0].name == "FSM1"
    assert type(single_ast.fsms[0]) == ast.FSM


def test_single_with_states():
    data = load_test_fsm('single_with_states.yml')
    single_ast = parser.parse_to_ast(data)
    assert len(single_ast.fsms) == 1
    assert single_ast.fsms[0].name == "FSM1"
    assert single_ast.fsms[0].gather_facts is False
    assert len(single_ast.fsms[0].states) == 2
    assert type(single_ast.fsms[0].states[0]) == ast.State
    assert single_ast.fsms[0].states[0].name == "Start"
    assert single_ast.fsms[0].states[1].name == "End"


def test_single_with_import_from():
    data = load_test_fsm('single_with_import_from.yml')
    single_ast = parser.parse_to_ast(data)
    assert len(single_ast.fsms) == 1
    assert single_ast.fsms[0].name == "FSM1"
    assert single_ast.fsms[0].gather_facts is False
    assert single_ast.fsms[0].import_from == 'tests/inputs/fsm1.yml'


def test_single_with_handlers():
    data = load_test_fsm('single_with_handlers.yml')
    single_ast = parser.parse_to_ast(data)
    assert len(single_ast.fsms) == 1
    assert single_ast.fsms[0].name == "FSM1"
    assert single_ast.fsms[0].gather_facts is False
    assert len(single_ast.fsms[0].states) == 2
    assert type(single_ast.fsms[0].states[0]) == ast.State
    assert len(single_ast.fsms[0].states[0].handlers) == 2
    assert len(single_ast.fsms[0].states[1].handlers) == 1
    assert len(single_ast.fsms[0].states[0].handlers) == 2
    assert type(single_ast.fsms[0].states[0].handlers[0]) == ast.Handler
    assert type(single_ast.fsms[0].states[0].handlers[1]) == ast.Handler
    assert single_ast.fsms[0].states[0].handlers[0].name == "enter"
    assert single_ast.fsms[0].states[0].handlers[1].name == "exit"
    assert single_ast.fsms[0].states[1].handlers[0].name == "enter"


def test_multiple():
    data = load_test_fsm('multiple.yml')
    multiple_ast = parser.parse_to_ast(data)
    assert len(multiple_ast.fsms) == 2
    assert multiple_ast.fsms[0].name == "FSM1"
    assert type(multiple_ast.fsms[0]) == ast.FSM
    assert multiple_ast.fsms[1].name == "FSM2"
    assert type(multiple_ast.fsms[1]) == ast.FSM
