
from collections import namedtuple
import yaml
import json


def serialize(message):
    return [message.__class__.__name__.encode(), yaml.dump(dict(message._asdict())).encode()]


def json_serialize(message):
    return json.dumps([message.__class__.__name__, dict(message._asdict())])


Event = namedtuple('Event', ['from_fsm_id', 'to_fsm_id', 'name', 'data'])
FSMTrace = namedtuple('FSMTrace', ['order', 'fsm_name', 'fsm_id', 'from_state', 'to_state', 'message_type'])
ChannelTrace = namedtuple('ChannelTrace', ['order', 'from_fsm', 'to_fsm', 'sent_message_type'])
ChangeState = namedtuple('ChangeState', ['order', 'from_fsm', 'to_fsm', 'sent_message_type'])
