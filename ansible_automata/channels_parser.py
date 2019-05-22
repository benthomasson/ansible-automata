
from . import channels_ast
from .parser import check_type, check_fields


def parse_to_channel(input_data):

    check_type(input_data, dict, "Channel elements should be a dict")
    check_fields(input_data, "Channel", [], ['name',
                                             'to_fsm',
                                             'from_fsm',
                                             'from_queue',
                                             'to_connector'])

    name = input_data.get('name', '')
    to_fsm = input_data.get('to_fsm', None)
    to_connector = input_data.get('to_connector', None)
    from_fsm = input_data.get('from_fsm', None)
    from_queue = input_data.get('from_queue', None)

    check_type(name, str, "Name should be a string")

    return channels_ast.Channel(name, from_fsm, from_queue, to_fsm, to_connector)


def parse_to_ast(input_data):

    channels = []
    new_ast = channels_ast.AST(channels)

    check_type(input_data, list, "Top level element should be a list")

    for element in input_data:
        channels.append(parse_to_channel(element))

    return new_ast
