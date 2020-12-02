# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from subprocess import call, Popen


class CaptureCommand:
    def __init__(self):
        self.asterisk_log_process = None

    def take_action(self):
        call(['mkdir', '-p', '/tmp/wazo-debug-capture'])
        self.asterisk_log_process = Popen('tail -f /var/log/asterisk/full > /tmp/wazo-debug-capture/asterisk-full', shell=True)
        self.wazo_auth_log_process = Popen('tail -f /var/log/wazo-auth.log > /tmp/wazo-debug-capture/wazo-auth.log', shell=True)

    def clean_up(self):
        if self.asterisk_log_process:
            self.asterisk_log_process.kill()
            self.asterisk_log_process.wait()
        if self.wazo_auth_log_process:
            self.wazo_auth_log_process.kill()
            self.wazo_auth_log_process.wait()


def main():
    command = CaptureCommand()
    try:
        command.take_action()
    except KeyboardInterrupt:
        command.clean_up()
