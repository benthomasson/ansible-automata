
from ansible_runner.automata import connectors_ast
from ansible_runner.automata import connectors_parser
import yaml
import os

HERE = os.path.abspath(os.path.dirname(__file__))


def load_test_data(name):
    with open(os.path.join(HERE, 'inputs', name)) as f:
        return yaml.safe_load(f.read())


def test_null():
    null_ast = connectors_parser.parse_to_ast(list())
    assert len(null_ast.connectors) == 0
    assert type(null_ast) == connectors_ast.AST


def test_single_channel():
    data = load_test_data('connectors_zmq.yml')
    single_ast = connectors_parser.parse_to_ast(data)
    assert len(single_ast.connectors) == 1
    assert single_ast.connectors[0].name == "zmq"
    assert type(single_ast.connectors[0]) == connectors_ast.Connector


def test_multiple_channel():
    data = load_test_data('connectors_websocket_zmq.yml')
    single_ast = connectors_parser.parse_to_ast(data)
    assert len(single_ast.connectors) == 2
    assert single_ast.connectors[0].name == "websocket"
    assert single_ast.connectors[0].type == "websocket"
    assert type(single_ast.connectors[0]) == connectors_ast.Connector
    assert single_ast.connectors[1].name == "zmq"
    assert single_ast.connectors[1].type == "zmq"
    assert type(single_ast.connectors[0]) == connectors_ast.Connector
