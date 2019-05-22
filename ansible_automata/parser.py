
from . import ast


class ParseException(Exception):

    pass


def check_required_fields(o, type_name, required_fields):

    for field in required_fields:
        if field not in o.keys():
            raise ParseException("{0} element requires field {1}".format(type_name, field))


def check_fields(o, type_name, required_fields, all_fields):

    check_required_fields(o, type_name, required_fields)

    for field in o.keys():
        if field not in all_fields:
            raise ParseException("Unknown field {1} in {0} element".format(type_name, field))


def check_type(o, types, message):
    if not isinstance(o, types):
        raise ParseException(message)


def parse_to_handler(name, body):

    check_type(body, list, "Handler element body should be a list of tasks")

    return ast.Handler(name, body)


def parse_to_state(input_data):

    check_type(input_data, dict, "State elements should be a dict")
    check_fields(input_data, "FSM", ['name'], ['name',
                                               'handlers'])

    name = input_data.get('name', '')
    handlers = input_data.get('handlers', {})

    check_type(name, str, "Name should a be string")
    check_type(handlers, dict, "Handlers should a be dict")

    new_handlers = []
    for handler_name, value in handlers.items():
        new_handlers.append(parse_to_handler(handler_name, value))

    return ast.State(name, new_handlers)


def parse_to_fsm(input_data):

    check_type(input_data, dict, "FSM elements should be a dict")
    check_fields(input_data, "FSM", ['name'], ['name',
                                               'hosts',
                                               'gather_facts',
                                               'roles',
                                               'states',
                                               'outputs',
                                               'import_from'])

    name = input_data.get('name', '')
    hosts = input_data.get('hosts', [])
    gather_facts = input_data.get('gather_facts', None)
    roles = input_data.get('roles', [])
    states = input_data.get('states', [])
    outputs = input_data.get('outputs', [])
    import_from = input_data.get('import_from', None)

    check_type(hosts, (list, str), "Hosts should a be list or string")
    check_type(gather_facts, (bool, str, type(None)), "gather_facts should a be a boolean or string")
    check_type(roles, list, "Roles should a be list")
    check_type(states, list, "States should a be list")
    check_type(outputs, list, "Outputs should a be list")

    new_states = []
    for state in states:
        new_states.append(parse_to_state(state))
    return ast.FSM(name, hosts, gather_facts, roles, new_states, outputs, import_from)


def parse_to_ast(input_data):

    fsms = []
    new_ast = ast.AST(fsms)

    check_type(input_data, list, "Top level element should be a list")

    for element in input_data:
        fsms.append(parse_to_fsm(element))

    return new_ast
