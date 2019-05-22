

from ansible_automata import messages
from ansible_runner.task_service.messages import Task, RunnerMessage

from gevent.queue import Empty

import logging
logger = logging.getLogger('ansible_automata.fsm')

DEFAULT_OUTPUT = 'default'


def handle_change_state(state, controller, task, msg_type, message):
    if 'when' in task:
        if not state.call_when(controller, task):
            return
    controller.self_channel.put((0, 0, messages.Event(controller.fsm_id,
                                                      controller.fsm_id,
                                                      'ChangeState',
                                                      dict(current_state=state.name,
                                                           next_state=task['change_state'],
                                                           handling_message_type=msg_type))))


def handle_shutdown(state, controller, task, msg_type, message):
    if 'when' in task:
        if not state.call_when(controller, task):
            return
    controller.self_channel.put((0, 0, messages.Event(controller.fsm_id,
                                                      controller.fsm_id,
                                                      'Shutdown',
                                                      dict(handling_message_type=msg_type))))


def handle_send_event(state, controller, task, msg_type, message):
    send_event = task['send_event']
    event_name = send_event.get('name', None)

    # Find the destination FSM to send the event to
    # First check for the FSM name in the send_event task
    # Second check for a mapping of the outboxes to FSMs
    # Third use the default mapping
    # If no FSM is found send no event.

    logger.info(send_event)
    logger.info(controller.outboxes)

    if 'fsm' in send_event:
        to_fsm_id = send_event['fsm']
    elif 'output' in send_event:
        to_fsm_id = controller.outboxes.get(send_event['output'], None)
    elif send_event.get('self', False):
        to_fsm_id = controller.name
    elif send_event.get('reply', False):
        to_fsm_id = message.from_fsm_id
    elif send_event.get('requeue', False):
        to_fsm_id = controller.name
        event_name = controller.last_event.name
    else:
        to_fsm_id = controller.outboxes.get(DEFAULT_OUTPUT, None)

    if send_event.get('send_received', False):
        data = controller.last_event.data.copy()
        logger.info('send_received with data %r', data)
        data.update(send_event.get('data', {}))
    elif send_event.get('requeue', False):
        data = controller.last_event.data.copy()
        logger.info('requeue with data %r', data)
        data.update(send_event.get('data', {}))
    else:
        logger.info('new data')
        data = send_event.get('data', {})

    if to_fsm_id is None:
        logger.info("Dropping event %s", send_event['name'])
        return

    logger.info("Sending %s to fsm %s from %s", event_name, to_fsm_id, controller.name)

    send_event_task = [dict(send_event=dict(event=event_name,
                                            data=data,
                                            to_fsm=to_fsm_id,
                                            from_fsm=controller.name,
                                            host='127.0.0.1',
                                            port=controller.control_socket_port))]
    if 'when' in task:
        send_event_task[0]['when'] = task['when']
    if 'with_items' in task:
        send_event_task[0]['with_items'] = task['with_items']
    if 'with_fileglob' in task:
        send_event_task[0]['with_fileglob'] = task['with_fileglob']

    controller.worker.queue.put(Task(next(controller.task_id_seq), 0, send_event_task))
    while True:
        worker_message = controller.worker_output_queue.get()
        if isinstance(worker_message, RunnerMessage):
            if worker_message.data.get('event_data', {}).get('task', None) == 'pause_for_kernel':
                pass
            elif worker_message.data.get('event_data', {}).get('task', None) == 'include_tasks':
                pass
            elif worker_message.data.get('event') == 'runner_on_skipped':
                return
            elif worker_message.data.get('event') == 'runner_on_ok':
                return


def handle_buffer_message(state, controller, task, msg_type, message):
    controller.message_buffer.put(message)


def handle_pop_message(state, controller, task, msg_type, message):
    try:
        message = controller.message_buffer.get(block=False)
        controller.self_channel.put((1, 0, message))
    except Empty:
        pass

