# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import datetime
import time

from cliff.command import Command
from subprocess import call, Popen


class CaptureCommand(Command):

    collection_directory = '/tmp/wazo-debug-capture'  # sanitize if replaced with user input

    def take_action(self, parsed_args):
        self.log_processes = []

        self._clear_directory()
        call(['mkdir', '-p', self.collection_directory])

        self._enable_agi_debug_mode()

        print('Starting capture...')
        self._log_start_date()
        self._capture_logs()
        self._capture_sip_rtp_packets()

        print('Capture started. Hit CTRL-C to stop the capture...')

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print()
            self.clean_up()

    def clean_up(self):
        for process in self.log_processes:
            process.kill()
            process.wait()

        self._log_stop_date()
        print('Capture stopped.')

        self._disable_agi_debug_mode()

        tarball_filename = '/tmp/wazo-debug-capture.tar.gz'
        self._make_capture_tarball(tarball_filename)
        print(f'Captured files have been stored in {tarball_filename}')

        self._clear_directory()

    def _capture_logs(self):
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
            'xivo-sync',
            'xivo-sysconfd',
            'xivo-upgrade',
        )
        for wazo_log in wazo_logs:
            self.log_processes.append(Popen(f'tail -f /var/log/{wazo_log}.log > {self.collection_directory}/{wazo_log}.log', shell=True))

    def _capture_sip_rtp_packets(self):
        # -O: Write captured data to pcap file
        # -N: Don't display sngrep interface, just capture
        # -q: Don't print captured dialogs in no interface mode
        # -r: Capture RTP packets payload
        self.log_processes.append(Popen(['sngrep', '-O', f'{self.collection_directory}/sngrep.pcap', '-N', '-q', '-r']))

    def _enable_agi_debug_mode(self):
        call(['asterisk', '-rx', 'agi set debug on'])

    def _disable_agi_debug_mode(self):
        call(['asterisk', '-rx', 'agi set debug off'])

    def _log_start_date(self):
        now = datetime.datetime.now().isoformat()
        with open(f'{self.collection_directory}/metadata.txt', 'a') as metadata_file:
            metadata_file.write(f'Start: {now}\n')

    def _log_stop_date(self):
        now = datetime.datetime.now().isoformat()
        with open(f'{self.collection_directory}/metadata.txt', 'a') as metadata_file:
            metadata_file.write(f'Stop: {now}\n')

    def _make_capture_tarball(self, tarball_filename):
        call(['tar', '-C', self.collection_directory, '-czf', tarball_filename, '.'])

    def _clear_directory(self):
        call(['rm', '-rf', self.collection_directory])


def main():
    command = CaptureCommand()
    command.take_action()
