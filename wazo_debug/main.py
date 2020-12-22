# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import sys

from cliff.app import App
from cliff.commandmanager import CommandManager


class WazoDebugApp(App):
    def __init__(self):
        super().__init__(
            description='Wazo Debug',
            command_manager=CommandManager('wazo_debug.commands'),
            version='1.0.0',
            deferred_help=True,
        )


def main(argv=sys.argv[1:]):
    myapp = WazoDebugApp()
    return myapp.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
