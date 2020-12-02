# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from subprocess import call, Popen


class CaptureCommand:
    def __init__(self):
        self.log_processes = []

    def take_action(self):
        call(['mkdir', '-p', '/tmp/wazo-debug-capture'])
        self.log_processes.append(Popen('tail -f /var/log/asterisk/full > /tmp/wazo-debug-capture/asterisk-full', shell=True))
        self.log_processes.append(Popen('tail -f /var/log/wazo-auth.log > /tmp/wazo-debug-capture/wazo-auth.log', shell=True))

    def clean_up(self):
        for process in self.log_processes:
            process.kill()
            process.wait()


def main():
    command = CaptureCommand()
    try:
        command.take_action()
    except KeyboardInterrupt:
        command.clean_up()
