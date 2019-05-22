
from . import connectors_ast
from .parser import check_type, check_required_fields


def parse_to_connector(input_data):

    check_type(input_data, dict, "Connector elements should be a dict")
    check_required_fields(input_data, "Connector", ['type', 'name'])

    name = input_data.get('name', '')
    type_name = input_data.get('name', '')

    check_type(name, str, "Name should be a string")
    check_type(type_name, str, "Type should be a string")

    return connectors_ast.Connector(type_name, name, input_data)


def parse_to_ast(input_data):

    connectors = []
    new_ast = connectors_ast.AST(connectors)

    check_type(input_data, list, "Top level element should be a list")

    for element in input_data:
        connectors.append(parse_to_connector(element))

    return new_ast
