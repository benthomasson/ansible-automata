

import gevent
import os
from gevent.queue import PriorityQueue, Queue
from pprint import pformat

from .conf import settings
from . import messages
from ansible_runner.task_service.worker import AnsibleTaskWorker
from ansible_runner.task_service.messages import Task, TaskComplete, RunnerMessage, ShutdownRequested, ShutdownComplete, RunnerStdout
import logging
import shutil
from itertools import count
from .command_handlers import registry as command_registry

logger = logging.getLogger('ansible_runner.automata.fsm')

NULL_EVENT = messages.Event(0, 0, 'null', {})

DEFAULT_OUTPUT = 'default'


def ensure_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


class _Channel(object):

    def __init__(self, from_fsm, to_fsm, tracer, queue=None):
        if queue is None:
            self.queue = PriorityQueue()
        else:
            self.queue = queue
        self.from_fsm = from_fsm
        self.to_fsm = to_fsm
        self.tracer = tracer

    def put(self, priority_order_item):
        priority, order, item = priority_order_item
        self.tracer.send_trace_message(messages.ChannelTrace(self.tracer.trace_order_seq(),
                                                             self.from_fsm.fsm_id if self.from_fsm else None,
                                                             self.to_fsm.fsm_id if self.to_fsm else None,
                                                             item.name))
        self.queue.put(priority_order_item)

    def get(self, block=True, timeout=None):
        return self.queue.get(block, timeout)

    receive = get


def Channel(from_fsm, to_fsm, tracer, queue=None):
    if settings.instrumented:
        return _Channel(from_fsm, to_fsm, tracer, queue)
    if queue is not None:
        return queue
    else:
        return PriorityQueue()


class _NullChannel(object):

    def __init__(self):
        pass

    def put(self, item):
        pass


NullChannelSingleton = _NullChannel()


class _NullChannelInstrumented(object):

    def __init__(self, from_fsm, tracer):
        self.from_fsm = from_fsm
        self.tracer = tracer

    def put(self, item):
        self.tracer.send_trace_message(messages.ChannelTrace(self.tracer.trace_order_seq(),
                                                             self.from_fsm.fsm_id,
                                                             None,
                                                             item.name))


def NullChannel(from_fsm, tracer):

    if settings.instrumented:
        return _NullChannelInstrumented(from_fsm, tracer)
    else:
        return NullChannelSingleton


class FSMController(object):

    def __init__(self, workspace, name, fsm_id, states, initial_state, tracer, channel_tracer, fsm_registry, fsm_id_seq, inventory, play_header, outputs):
        self.workspace = workspace
        self.inventory = inventory
        self.shutting_down = False
        self.is_shutdown = False
        self.fsm_registry = fsm_registry
        self.name = name
        self.fsm_id = fsm_id
        self.tracer = tracer
        self.channel_tracer = channel_tracer
        self.state = initial_state
        self.states = states
        self.inbox = PriorityQueue()
        self.message_buffer = Queue()
        self.self_channel = Channel(self, self, tracer, self.inbox)
        self.setup_worker_private_data_dir(os.path.join(workspace, 'automata', name))
        self.worker = AnsibleTaskWorker(os.path.join(workspace, 'automata', name),
                                        tracer,
                                        next(fsm_id_seq),
                                        None,
                                        play_header)
        self.worker_output_queue = Queue()
        self.worker.controller.outboxes['output'] = self.worker_output_queue
        self.outboxes = dict(default=None)
        self.last_event = NULL_EVENT
        self.task_id_seq = count(0)
        self.message_id_seq = count(0)
        self.failure_count = 0
        if outputs:
            self.outboxes.update({name: None for name in outputs})
        self.thread = gevent.spawn(self.receive_messages)

    def setup_worker_private_data_dir(self, worker_private_data_dir):
        ensure_directory(worker_private_data_dir)
        with open(os.path.join(worker_private_data_dir, 'README'), 'w') as f:
            f.write("This directory contains generated files that will be overwritten on the next execution.  Editing these files is not recommended.")
        env_full_path = os.path.join(self.workspace, 'env')
        if self.inventory:
            inventory_full_path = os.path.join(self.workspace, self.inventory)
        else:
            inventory_full_path = os.path.join(self.workspace, 'inventory')
        if inventory_full_path and os.path.exists(inventory_full_path):
            if os.path.exists(os.path.join(worker_private_data_dir, 'inventory')):
                shutil.rmtree(os.path.join(worker_private_data_dir, 'inventory'))
            shutil.copytree(inventory_full_path, os.path.join(worker_private_data_dir, 'inventory'))
        if os.path.exists(env_full_path):
            if os.path.exists(os.path.join(worker_private_data_dir, 'env')):
                shutil.rmtree(os.path.join(worker_private_data_dir, 'env'))
            shutil.copytree(env_full_path, os.path.join(worker_private_data_dir, 'env'))

    def enter(self):
        self.state.exec_handler(self, 'enter', NULL_EVENT)

    def change_state(self, state, handling_message_type):
        if self.state:
            self.state.exec_handler(self, 'exit', NULL_EVENT)
        if settings.instrumented:
            self.tracer.send_trace_message(messages.FSMTrace(self.tracer.trace_order_seq(),
                                                             self.name,
                                                             self.fsm_id,
                                                             self.state.name,
                                                             state.name,
                                                             handling_message_type))
        self.state = state
        if self.state:
            self.state.exec_handler(self, 'enter', NULL_EVENT)

    def handle_message(self, message_type, message):
        self.state.exec_handler(self, message_type, message)

    def shutdown(self):
        self.shutting_down = True
        if self.is_shutdown:
            return
        self.worker.queue.put(ShutdownRequested())
        for _ in range(10):
            gevent.sleep(1)
            worker_message = self.worker_output_queue.get()
            if isinstance(worker_message, ShutdownComplete):
                break
        self.is_shutdown = True

    def receive_messages(self):

        while not self.shutting_down:
            gevent.sleep(0.1)
            logger.info("Waiting for messages")
            priority, order, message = self.inbox.get()
            if self.shutting_down:
                logger.info("Ignoring message due to shutdown")
                break
            message_type = message.name
            if message_type == 'Shutdown':
                logger.info("Shutting down")
                self.shutdown()
                break
            elif message_type == 'ChangeState' and self.state.name != message.data['current_state']:
                logger.info("Ignoring ChangeState message because the current state does not match")
            elif message_type == 'ChangeState' and self.state.name == message.data['current_state']:
                logger.info("Changing state")
                self.change_state(self.states[message.data['next_state']],
                                  message.data['handling_message_type'])
            else:
                logger.info("Handling message {}".format(message_type))
                self.handle_message(message_type, message)


class State(object):

    def __init__(self, name, handlers):
        self.name = name
        self.handlers = handlers

    def call_set_fact(self, controller, data, sub_dict=None):
        task_id = next(controller.task_id_seq)
        set_fact_args = dict(cacheable=True)
        if sub_dict:
            set_fact_args[sub_dict] = data
        else:
            set_fact_args.update(data)
        controller.worker.queue.put(Task(task_id,
                                         0,
                                         [dict(set_fact=set_fact_args)]))
        while True:
            worker_message = controller.worker_output_queue.get()
            if worker_message.id is None:
                continue
            if worker_message.id < task_id:
                continue
            if isinstance(worker_message, TaskComplete):
                break

    def call_when(self, controller, task):
        task_id = next(controller.task_id_seq)
        controller.worker.queue.put(Task(task_id,
                                         0,
                                         [dict(when_helper=None,
                                               when=task['when'])]))
        while True:
            worker_message = controller.worker_output_queue.get()
            if isinstance(worker_message, RunnerMessage):

                logger.info("worker_message.id %s", worker_message.id)
                if worker_message.id is None:
                    continue
                if worker_message.id < task_id:
                    continue
                if worker_message.data.get('event_data', {}).get('task', None) == 'pause_for_kernel':
                    pass
                elif worker_message.data.get('event_data', {}).get('task', None) == 'include_tasks':
                    pass
                elif worker_message.data.get('event') == 'runner_on_skipped':
                    return False
                elif worker_message.data.get('event') == 'runner_on_ok':
                    return True

    def exec_handler(self, controller, msg_type, message):
        if msg_type in self.handlers:
            if message.name not in ['null', 'failure']:
                controller.last_event = message
            if message.data:
                logger.info("Setting facts %s for %s", message.data, message.name)
                self.call_set_fact(controller, message.data, 'event')
            else:
                logger.info("No facts for %s", message.name)
            for task in self.handlers[msg_type]:
                task_id = next(controller.task_id_seq)
                task_failed = False
                found_special_handler = False
                special_handler = None
                new_data = None
                worker_message = None
                for cmd in command_registry.keys():
                    # task is a dict
                    if cmd in task:
                        found_special_handler = True
                        special_handler = command_registry[cmd]
                        special_handler(self, controller, task, msg_type, message)
                        break
                if not found_special_handler:
                    logger.info('Running task %s %s', task_id, task)
                    controller.worker.queue.put(Task(task_id, 0, [task]))
                    while True:
                        worker_message = controller.worker_output_queue.get()
                        logger.info("Received message type %s id %s", type(worker_message).__name__, worker_message.id)
                        if worker_message.id is None:
                            logger.info("dropped: %s", pformat(worker_message))
                            continue
                        if worker_message.id < task_id:
                            logger.info("dropped: %s", pformat(worker_message))
                            continue
                        if isinstance(worker_message, RunnerMessage):
                            if worker_message.data.get('event_data', {}).get('task', None) == 'pause_for_kernel':
                                pass
                            elif worker_message.data.get('event_data', {}).get('task', None) == 'include_tasks':
                                pass
                            else:
                                if worker_message.data.get('event') == 'runner_on_failed':
                                    task_failed = True
                                    logger.info('Task failed  %s', task)
                        elif isinstance(worker_message, TaskComplete):
                            if task_failed:
                                logger.info('Calling failure handler')
                                controller.failure_count += 1
                                new_data = message.data.copy()
                                new_data['failure_count'] = controller.failure_count
                                logger.info('new_data %s', new_data)
                                controller.self_channel.put((0, 0, messages.Event(controller.fsm_id,
                                                                                  controller.fsm_id,
                                                                                  'failure',
                                                                                  new_data)))

                                return
                            else:
                                break
                        elif isinstance(worker_message, RunnerStdout):
                            pass
                        else:
                            logger.info("unhandled: %s", pformat(worker_message))


class _NullTracer(object):

    def trace_order_seq(self):
        return 0

    def send_trace_message(self, message):
        pass


NullTracer = _NullTracer()
