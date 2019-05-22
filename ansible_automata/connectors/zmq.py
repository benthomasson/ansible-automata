
import zmq.green as zmq
import gevent
from gevent.queue import PriorityQueue
import yaml
from .. import messages
from itertools import count
import logging

logger = logging.getLogger('ansible_automata.connectors.zmq')


class ZMQEventChannel(object):

    def __init__(self, fsm_registry, connector_registry, configuration):
        self.fsm_registry = fsm_registry
        self.connector_registry = connector_registry
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.ROUTER)
        if 'bind_port' in configuration:
            self.socket_port = configuration.get('bind_port')
            self.socket.bind('tcp://{0}:{1}'.format(configuration.get('bind_address', '127.0.0.1'),
                                                    self.socket_port))
        else:
            self.socket_port = self.socket.bind_to_random_port('tcp://{0}'.format(configuration.get('bind_address', '127.0.0.1')))
        logger.info('starting zmq_thread')
        self.zmq_thread = gevent.spawn(self.receive_external_messages)
        self.inbox_thread = gevent.spawn(self.receive_internal_messages)
        self.inbox = PriorityQueue()
        self.message_id_seq = count(0)
        self.client_id_seq = count(0)
        self.clients = dict()

    def receive_internal_messages(self):
        while True:
            gevent.sleep(0.1)
            logger.info("Waiting for messages")
            priority, order, message = self.inbox.get()
            message_type = message.name
            logger.info('Received %s', message_type)
            if 'client_id' in message.data and message.data['client_id'] in self.clients:
                #Unicast
                logger.info("Unicasting message to %s aka %r", message.data['client_id'], self.clients[message.data['client_id']])
                msg = [self.clients[message.data['client_id']]]
                msg.extend(messages.serialize(message))
                self.socket.send_multipart(msg)
            else:
                #Broadcast
                logger.info("Broadcasting message to all listening clients")
                for client_id in list(self.clients.values()):
                    msg = [client_id]
                    msg.extend(messages.serialize(message))
                    self.socket.send_multipart(msg)

    def receive_external_messages(self):
        while True:
            to_fsm_id = None
            from_fsm_id = None
            zmq_client_id = None
            logger.info('waiting on recv_multipart')
            message = self.socket.recv_multipart()
            logger.info(repr(message))
            zmq_client_id = message.pop(0)
            client_id = str(next(self.client_id_seq))
            self.clients[client_id] = zmq_client_id
            try:
                msg_type = message.pop(0).decode()
                msg_data = yaml.safe_load(message.pop(0).decode())
                if b'Listening' in message:
                    msg_data['data']['client_id'] = client_id
                logger.info(repr(msg_type))
                logger.info(repr(msg_data))
            except Exception as e:
                self.socket.send_multipart([zmq_client_id, b'Error'])
                logger.error(str(e))
                continue
            if not isinstance(msg_type, str):
                self.socket.send_multipart([zmq_client_id, 'Element 1 should be str was {}'.format(type(msg_type)).encode()])
                logger.error([zmq_client_id, 'Element 1 should be str was {}'.format(type(msg_type)).encode()])
                continue
            if not isinstance(msg_data, dict):
                self.socket.send_multipart([zmq_client_id, 'Element 2 should be a dict was {}'.format(type(msg_data)).encode()])
                logger.error([zmq_client_id, 'Element 2 should be a dict was {}'.format(type(msg_data)).encode()])
                continue
            to_fsm_id = msg_data.get('to_fsm_id', None)
            from_fsm_id = msg_data.get('from_fsm_id', None)
            if not from_fsm_id:
                from_fsm_id = 'zmq'
            if to_fsm_id in self.fsm_registry:
                logger.info('Sending to FSM {} from {}'.format(to_fsm_id, from_fsm_id))
                self.fsm_registry[to_fsm_id].inbox.put((1,
                                                        next(self.fsm_registry[to_fsm_id].message_id_seq),
                                                        messages.Event(from_fsm_id,
                                                                       to_fsm_id,
                                                                       msg_data['name'],
                                                                       msg_data['data'])))

                logger.info('Processed')
                self.socket.send_multipart([zmq_client_id, b'Processed'])
            else:
                logger.info('Not processed')
                self.socket.send_multipart([zmq_client_id, b'Not processed'])
            gevent.sleep(0)
