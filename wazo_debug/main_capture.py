# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from subprocess import call, Popen


class CaptureCommand:
    collection_directory = '/tmp/wazo-debug-capture'  # sanitize if replaced with user input

    def __init__(self):
        self.log_processes = []

    def take_action(self):
        print('Starting capture...')
        self._clear_directory()
        call(['mkdir', '-p', self.collection_directory])
        self.log_processes.append(Popen(f'tail -f /var/log/asterisk/full > {self.collection_directory}/asterisk-full', shell=True))
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
            self.log_processes.append(Popen(f'tail -f /var/log/{wazo_log}.log > {self.collection_directory}/{wazo_log}.log', shell=True))
        print('Capture started. Hit CTRL-C to stop the capture...')
        while True:
            time.sleep(1)

    def clean_up(self):
        print()
        for process in self.log_processes:
            process.kill()
            process.wait()
        print('Capture stopped.')
        call(['tar', '-C', self.collection_directory, '-czf', '/tmp/wazo-debug-capture.tar.gz', '.'])
        print('Captured files have been stored in /tmp/wazo-debug-capture.tar.gz')
        self._clear_directory()

    def _clear_directory(self):
        call(['rm', '-rf', self.collection_directory])


def main():
    command = CaptureCommand()
    try:
        command.take_action()
    except KeyboardInterrupt:
        command.clean_up()
