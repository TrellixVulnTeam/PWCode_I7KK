# MIT License

# Original work Copyright (c) 2018 François Girault
# Modified work Copyright 2020 Morten Eek

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import settings


class Command:
    """Base class for commands meant to be displayed in the palette """

    def __init__(
        self,
        name,
        category="",
        title="",
        description="",
        shortcut="",
        command_callable=None,
    ):
        self.name = name
        self.title = title
        self.description = description
        self.shortcut = shortcut
        # callable
        self.command_callable = command_callable

    def __call__(self, app, *args, **kwargs):
        """Execute the callable self.command"""
        self.command_callable(app, *args, **kwargs)


class Commander:
    """A class that handle execution of command instance. """

    COMMANDS = []

    COMMAND_DICT = {}

    def __init__(self, app):
        self.app = app
        self.history = []
        # self.build_commands()

    @classmethod
    def add_command(cls, cmd):
        """register a command"""
        cls.COMMANDS.append(cmd)
        cls.COMMAND_DICT[cmd.name] = cmd

    def run(self, cmd, *args, **kwargs):
        """Execute a command and add it to the history"""
        if isinstance(cmd, str):
            cmd = self.COMMAND_DICT[cmd]
        cmd(self.app, *args, **kwargs)
        self.history.append((cmd, args, kwargs))


def command(category="", title="", description="", shortcut=""):
    """a decorator to register commentsands"""

    def _register_decorator(func):
        """wrapper"""
        Commander.add_command(
            Command(
                func.__name__,
                category,
                title,
                description,
                shortcut,
                command_callable=func,
            )
        )
        return func

    return _register_decorator
