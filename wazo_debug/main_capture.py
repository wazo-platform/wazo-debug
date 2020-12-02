# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from subprocess import call, Popen


class CaptureCommand:
    def __init__(self):
        self.log_processes = []

    def take_action(self):
        print('Starting capture...')
        call(['rm', '-rf', '/tmp/wazo-debug-capture'])
        call(['mkdir', '-p', '/tmp/wazo-debug-capture'])
        self.log_processes.append(Popen('tail -f /var/log/asterisk/full > /tmp/wazo-debug-capture/asterisk-full', shell=True))
        wazo_logs = (
            'wazo-auth',
            'wazo-agentd',
            'wazo-agid',
            'wazo-amid',
            'wazo-auth',
            'wazo-calld',
            'wazo-call-logd',
            'wazo-chatd',
            'wazo-confd',
            'wazo-confgend',
            'wazo-deployd',
            'wazo-dird',
            'wazo-dxtora',
            'wazo-phoned',
            'wazo-plugind',
            'wazo-provd',
            'wazo-purge-db',
            'wazo-setupd',
            'wazo-stat',
            'wazo-upgrade',
            'wazo-webhookd',
            'wazo-websocketd',
        )
        for wazo_log in wazo_logs:
            self.log_processes.append(Popen(f'tail -f /var/log/{wazo_log}.log > /tmp/wazo-debug-capture/{wazo_log}.log', shell=True))
        print('Capture started. Hit CTRL-C to stop the capture...')
        while True:
            time.sleep(1)

    def clean_up(self):
        for process in self.log_processes:
            process.kill()
            process.wait()
        print('Capture stopped.')


def main():
    command = CaptureCommand()
    try:
        command.take_action()
    except KeyboardInterrupt:
        command.clean_up()
