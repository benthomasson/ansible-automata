import pkg_resources

from . import builtin_commands

plugins = {
    entry_point.name: entry_point.load()
    for entry_point
    in pkg_resources.iter_entry_points('ansible_automata.command_plugins')
}

registry = { name: plugin.command_plugin for name, plugin in plugins.items()}

#Built-in commands
registry['change_state'] = builtin_commands.handle_change_state
registry['shutdown'] = builtin_commands.handle_shutdown
registry['send_event'] = builtin_commands.handle_send_event
registry['buffer_message'] = builtin_commands.handle_buffer_message
registry['pop_message'] = builtin_commands.handle_pop_message

