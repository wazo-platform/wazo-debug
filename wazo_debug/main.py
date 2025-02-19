# Copyright 2020-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import sys

from cliff.app import App
from cliff.commandmanager import CommandManager
from xivo import xivo_logging

from . import config


class WazoDebugApp(App):
    def __init__(self):
        super().__init__(
            description='Wazo Debug',
            command_manager=CommandManager('wazo_debug.commands'),
            version='1.1.0',
            deferred_help=True,
        )
        self.config = None

    def build_option_parser(self, *args, **kwargs):
        parser = super().build_option_parser(*args, **kwargs)
        parser.add_argument(
            '--config',
            default='/etc/wazo-debug',
            help='The wazo-debug configuration directory',
        )
        return parser

    def initialize_app(self, argv):
        self.config = config.build(self.options)


def main(argv=sys.argv[1:]):
    xivo_logging.silence_loggers(
        [
            'urllib3',
            'stevedore.extension',
        ],
        logging.WARNING,
    )
    myapp = WazoDebugApp()
    return myapp.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
