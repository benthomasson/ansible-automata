
from ansible_runner.automata import channels_ast
from ansible_runner.automata import channels_parser
import yaml
import os

HERE = os.path.abspath(os.path.dirname(__file__))


def load_test_data(name):
    with open(os.path.join(HERE, 'inputs', name)) as f:
        return yaml.safe_load(f.read())


def test_null():
    null_ast = channels_parser.parse_to_ast(list())
    assert len(null_ast.channels) == 0
    assert type(null_ast) == channels_ast.AST


def test_single_channel():
    data = load_test_data('channel_single.yml')
    single_ast = channels_parser.parse_to_ast(data)
    assert len(single_ast.channels) == 1
    assert single_ast.channels[0].name == "Single"
    assert type(single_ast.channels[0]) == channels_ast.Channel


def test_multiple_channel():
    data = load_test_data('channel_multiple.yml')
    single_ast = channels_parser.parse_to_ast(data)
    assert len(single_ast.channels) == 2
    assert single_ast.channels[0].name == "Channel1"
    assert type(single_ast.channels[0]) == channels_ast.Channel
    assert single_ast.channels[1].name == "Channel2"
    assert type(single_ast.channels[0]) == channels_ast.Channel
    assert single_ast.channels[0].from_fsm == "FSM1"
    assert single_ast.channels[0].to_fsm == "FSM2"
    assert single_ast.channels[1].from_fsm == "FSM2"
    assert single_ast.channels[1].from_queue is None
    assert single_ast.channels[1].to_connector == "zmq"
