
import gevent
import yaml
import os
from itertools import count

from .connectors import registry as connectors_type_registry

from . import parser as fsm_parser
from . import channels_parser as channels_parser
from . import connectors_parser as connectors_parser
from .connectors import ZMQEventChannel

from .tracer import FileSystemTraceLog
from .ast import FSM
from .fsm import FSMController, State


def ansible_automata_run(workspace, automata_file, inventory=None, channels_file=None, connectors_file=None):

    # Check for input files
    automata_file_full_path = os.path.join(workspace, 'project', automata_file)
    if not os.path.exists(automata_file_full_path):
        raise Exception('Could not find automata definition file in {0}'.format(automata_file_full_path))

    if channels_file:
        channels_file_full_path = os.path.join(workspace, 'project', channels_file)
        if not os.path.exists(channels_file_full_path):
            raise Exception('Could not find channels file in {0}'.format(channels_file_full_path))
    else:
        channels_file_full_path = None

    if connectors_file:
        connectors_file_full_path = os.path.join(workspace, 'project', connectors_file)
        if not os.path.exists(connectors_file_full_path):
            raise Exception('Could not find connectors file in {0}'.format(connectors_file_full_path))
    else:
        connectors_file_full_path = None

    if inventory:
        inventory_full_path = os.path.join('workspace', inventory)
        if not os.path.exists(inventory_full_path):
            raise Exception('Could not find inventory in {0}'.format(inventory_full_path))

    # Build the FSMs
    with open(automata_file_full_path) as f:
        data = yaml.safe_load(f.read())

    fsm_registry = dict()
    connectors_registry = fsm_registry

    ast = fsm_parser.parse_to_ast(data)

    tracer = FileSystemTraceLog('fsm.log')

    fsms = []

    fsm_id_seq = count(0)

    for fsm in ast.fsms:
        if fsm.import_from is not None:
            with open(fsm.import_from) as f:
                data = yaml.safe_load(f.read())
                imported_fsm = fsm_parser.parse_to_fsm(data)
                fsm = FSM(fsm.name or imported_fsm.name,
                          fsm.hosts or imported_fsm.hosts,
                          fsm.gather_facts if fsm.gather_facts is not None else imported_fsm.gather_facts,
                          fsm.roles or imported_fsm.roles,
                          fsm.states or imported_fsm.states,
                          fsm.outputs or imported_fsm.outputs,
                          None)
        play_header = dict(name=fsm.name,
                           hosts=fsm.hosts,
                           gather_facts=fsm.gather_facts)
        fsm_id = next(fsm_id_seq)
        states = {}
        for state in fsm.states:
            handlers = {}
            for handler in state.handlers:
                handlers[handler.name] = handler.body
            states[state.name] = State(state.name, handlers)
        if 'Start' not in states:
            raise Exception('Missing required "Start" state in FSM: "{0}"'.format(fsm.name))
        fsm_controller = FSMController(workspace,
                                       fsm.name,
                                       fsm_id,
                                       states,
                                       states.get('Start'),
                                       tracer,
                                       tracer,
                                       fsm_registry,
                                       fsm_id_seq,
                                       inventory,
                                       play_header,
                                       fsm.outputs)
        fsms.append(fsm_controller)

    fsm_threads = [x.thread for x in fsms]

    # Build the FSM registry
    fsm_registry.update({x.name: x for x in fsms})

    # Wire up FSM using channels
    if channels_file_full_path:
        with open(channels_file_full_path) as f:
            data = yaml.safe_load(f.read())

        channels_ast = channels_parser.parse_to_ast(data)

        for channel in channels_ast.channels:
            from_fsm = fsm_registry.get(channel.from_fsm, None)
            if from_fsm is None:
                raise Exception('Could not find an FSM named {} for channel {}'.format(channel.from_fsm, channel.name))
            to_fsm = fsm_registry.get(channel.to_fsm, None)
            if from_fsm is None:
                raise Exception('Could not find an FSM named {} for channel {}'.format(channel.from_fsm, channel.name))
            if channel.from_queue is not None:
                if channel.from_queue not in from_fsm.outboxes:
                    raise Exception('On {} FSM Could not find an output named {} for channel {}'.format(channel.from_fsm, channel.from_queue, channel.name))
                from_fsm.outboxes[channel.from_queue] = to_fsm.name
            else:
                from_fsm.outboxes['default'] = to_fsm.name

    # Adds connectors for external events
    connectors = []
    if connectors_file_full_path:
        with open(connectors_file_full_path) as f:
            connectors_spec = connectors_parser.parse_to_ast(yaml.safe_load(f.read()))
            for connector_spec in connectors_spec.connectors:
                if connector_spec.type not in connectors_type_registry:
                    raise Exception('Could not find the {0} connector'.format(connector_spec.type))
                connector = connectors_type_registry[connector_spec.type](fsm_registry, connectors_registry, connector_spec.config)
                connectors.append(connector)
                connectors_registry[connector_spec.name] = connector

    for connector in connectors:
        if isinstance(connector, ZMQEventChannel):
            control_socket_port = connector.socket_port
            break
    else:
        connector = ZMQEventChannel(fsm_registry, connectors_registry, {})
        control_socket_port = connector.socket_port
        connectors.append(connector)
        connectors_registry['zmq'] = connector

    # Start the FSMs by calling enter on all the FSMs.
    for fsm in fsms:
        fsm.control_socket_port = control_socket_port
        fsm.enter()

    # Start all the greenlets for the FSMs
    try:
        gevent.joinall(fsm_threads)
    except KeyboardInterrupt:
        print('Caught KeyboardInterrupt')
    finally:
        print('Shutting down...')
        for fsm in fsms:
            fsm.shutdown()
        print('Successful shutdown')
    return 0
