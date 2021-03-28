"""CommandParser module.
Idea of the module is to create a common interface for custom commands set.
Commands must start from the special prefix '/' (may be improved later).
Parameters must be separated from the command by a space and can be splitted by space,
dot, colon and semicolon.
"""

import re

COMMAND_PREFIX = '/'
COMMAND_SEPARATOR = ' '
PARAMS_SEPARATORS = '[,\s\.;]+'


class CommandDescription():
    '''
    Single command definition
    '''

    def __init__(self, id, method, names, help, nargs=None, arg_name=None):
        self.id = id
        self.names = names
        self.help = help
        self.nargs = nargs
        self.arg_name = arg_name
        self.method = method
        # Default value to create one-param commands conviniently.
        if arg_name and not self.nargs:
            self.nargs = '1'
        if nargs and not arg_name:
            self.arg_name = 'param'

    def getArgsHelp(self):
        if self.nargs == '1':
            return '<{}>'.format(self.arg_name)

        if self.nargs == '?':
            return '(<{}>)'.format(self.arg_name)

        if self.nargs == '*':
            return '<{}1> <{}2>...'.format(self.arg_name, self.arg_name)

        return None

    def getHelp(self):
        result = []
        result += [COMMAND_PREFIX + name for name in self.names]
        if self.nargs:
            result += [self.getArgsHelp()]
        result += ['-', self.help]
        return ' '.join(result)


class Command():
    """Actual command instance"""

    def __init__(self, id, params):
        self.id = id
        self.params = params


class CommandParser():
    """Class for parsing custom commands"""

    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        self.commands = []

    def registerCommand(self, id, method, name, help, nargs=None, arg_name=None):
        """
        Register new command with the given set of names

        Keyword arguments:
        id -- Unique external identifier of the command.
        method - Method to run when the command is executed.
        name -- Name of the command or list of possible names.
        help -- Human-readable description of the command.
        nargs -- Argument counter (for help only). Can be '1', '?', '*'. Optional.
        arg_name -- Name of the argument (for help only). Optional.
        """
        if type(name) is not list:
            name = [name]
        self.commands.append(CommandDescription(id, method, name, help, nargs, arg_name))
        self.dispatcher.register_message_handler(method, commands=name)

    def getHelp(self):
        return '\n'.join([c.getHelp() for c in self.commands])

    def parse(self, input):
        if not input.startswith(COMMAND_PREFIX):
            return None

        command_index = input.find(COMMAND_SEPARATOR)
        if command_index < 0:
            name = input[1:]
            params = []
        else:
            name = input[1:command_index]
            params = re.split(PARAMS_SEPARATORS, input[command_index + 1:])

        for c in self.commands:
            if name in c.names:
                return Command(c.id, params)
        return None
