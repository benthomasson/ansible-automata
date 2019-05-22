"""
Defines and configures connectors that send events to the automata.
"""

import pkg_resources

from .zmq import ZMQEventChannel

plugins = {
    entry_point.name: entry_point.load()
    for entry_point
    in pkg_resources.iter_entry_points('ansible_automata.connector_plugins')
}

registry = { name: plugin.connector_plugin for name, plugin in plugins.items()}

#Always set zmq to the ZMQEventChannel connector plugin
registry['zmq'] = ZMQEventChannel

