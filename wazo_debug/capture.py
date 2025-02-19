# Copyright 2020-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import datetime
import logging
import os.path
import signal
import time
from subprocess import PIPE, Popen, call

from cliff.command import Command
from requests import RequestException
from wazo_amid_client import Client as AmidClient
from wazo_auth_client import Client as AuthClient
from wazo_call_logd_client import Client as CallLogdClient
from wazo_calld_client import Client as CalldClient
from wazo_chatd_client import Client as ChatdClient
from wazo_dird_client import Client as DirdClient
from wazo_webhookd_client import Client as WebhookdClient

logger = logging.getLogger(__name__)


class TokenCreationError(Exception):
    pass


class CaptureCommand(Command):
    "Capture live events happening on a Wazo server"

    # sanitize if replaced with user input
    collection_directory = '/tmp/wazo-debug-capture'

    def take_action(self, parsed_args):
        self.log_processes = []
        self._start_capture()

        print('Capture started. Hit CTRL-C to stop the capture...')

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print()
            self._stop_capture()

    def _start_capture(self):
        self._clear_directory()
        call(['mkdir', '-p', self.collection_directory])

        self._enable_agi_debug_mode()
        try:
            self.token = self._create_token()
        except TokenCreationError as e:
            logger.error('Error creating token. Could not enable debug logs: %s', e)
        else:
            self._enable_wazo_auth_debug_logs(self.token)
            self._enable_wazo_calld_debug_logs(self.token)
            self._enable_wazo_call_logd_debug_logs(self.token)
            self._enable_wazo_webhookd_debug_logs(self.token)
            self._enable_wazo_amid_debug_logs(self.token)
            self._enable_wazo_dird_debug_logs(self.token)
            self._enable_wazo_chatd_debug_logs(self.token)

        print('Starting capture...')
        self._log_version()
        self._log_start_date()
        self._capture_logs()
        self._capture_network_packets()
        self._capture_sip_rtp_packets()

    def _stop_capture(self):
        for process in self.log_processes:
            process.send_signal(signal.SIGINT)
            process.wait()
            if process.returncode != 0 and process.stderr:
                print(process.stderr.read().decode('utf-8'))

        self._log_stop_date()
        print('Capture stopped.')

        try:
            self.token = self._create_token()
        except TokenCreationError as e:
            logger.error('Error creating token. Could not disable debug logs: %s', e)
        else:
            self._disable_wazo_webhookd_debug_logs(self.token)
            self._disable_wazo_call_logd_debug_logs(self.token)
            self._disable_wazo_calld_debug_logs(self.token)
            self._disable_wazo_auth_debug_logs(self.token)
            self._disable_wazo_amid_debug_logs(self.token)
            self._disable_wazo_dird_debug_logs(self.token)
            self._disable_wazo_chatd_debug_logs(self.token)

        self._disable_agi_debug_mode()

        tarball_filename = '/tmp/wazo-debug-capture.tar.gz'
        self._make_capture_tarball(tarball_filename)
        print(f'Captured files have been stored in {tarball_filename}')

        self._clear_directory()

    def _capture_logs(self):
        command = f'tail -f /var/log/asterisk/full > {self.collection_directory}/asterisk-full'
        self.log_processes.append(Popen(command, shell=True))
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
            'wazo-dird',
            'wazo-dxtora',
            'wazo-phoned',
            'wazo-plugind',
            'wazo-provd',
            'wazo-purge-db',
            'wazo-setupd',
            'wazo-stat',
            'wazo-sync',
            'wazo-sysconfd',
            'wazo-upgrade',
            'wazo-webhookd',
            'wazo-websocketd',
            'xivo-sync',  # deprecated in 24.01
            'xivo-upgrade',
        )
        for wazo_log in wazo_logs:
            log_file_path = f'/var/log/{wazo_log}.log'
            if not os.path.exists(log_file_path):
                continue
            command = f'tail -f /var/log/{wazo_log}.log > {self.collection_directory}/{wazo_log}.log'
            self.log_processes.append(Popen(command, shell=True))

    def _create_token(self):
        client = AuthClient(**self.app.config['auth'])
        try:
            return client.token.new(backend='wazo_user')['token']
        except RequestException as e:
            raise TokenCreationError(e)

    def _enable_wazo_auth_debug_logs(self, token):
        client = AuthClient(**self.app.config['auth'], token=token)
        self._enable_service_debug_logs(client)

    def _disable_wazo_auth_debug_logs(self, token):
        client = AuthClient(**self.app.config['auth'], token=token)
        self._disable_service_debug_logs(client)

    def _enable_wazo_calld_debug_logs(self, token):
        client = CalldClient(**self.app.config['calld'], token=token)
        self._enable_service_debug_logs(client)

    def _disable_wazo_calld_debug_logs(self, token):
        client = CalldClient(**self.app.config['calld'], token=token)
        self._disable_service_debug_logs(client)

    def _enable_wazo_call_logd_debug_logs(self, token):
        client = CallLogdClient(**self.app.config['call-logd'], token=token)
        self._enable_service_debug_logs(client)

    def _disable_wazo_call_logd_debug_logs(self, token):
        client = CallLogdClient(**self.app.config['call-logd'], token=token)
        self._disable_service_debug_logs(client)

    def _enable_wazo_webhookd_debug_logs(self, token):
        client = WebhookdClient(**self.app.config['webhookd'], token=token)
        self._enable_service_debug_logs(client)

    def _disable_wazo_webhookd_debug_logs(self, token):
        client = WebhookdClient(**self.app.config['webhookd'], token=token)
        self._disable_service_debug_logs(client)

    def _enable_wazo_amid_debug_logs(self, token):
        client = AmidClient(**self.app.config['amid'], token=token)
        self._enable_service_debug_logs(client)

    def _disable_wazo_amid_debug_logs(self, token):
        client = AmidClient(**self.app.config['amid'], token=token)
        self._disable_service_debug_logs(client)

    def _enable_wazo_chatd_debug_logs(self, token):
        client = ChatdClient(**self.app.config['chatd'], token=token)
        self._enable_service_debug_logs(client)

    def _disable_wazo_chatd_debug_logs(self, token):
        client = ChatdClient(**self.app.config['chatd'], token=token)
        self._disable_service_debug_logs(client)

    def _enable_wazo_dird_debug_logs(self, token):
        client = DirdClient(**self.app.config['dird'], token=token)
        self._enable_service_debug_logs(client)

    def _disable_wazo_dird_debug_logs(self, token):
        client = DirdClient(**self.app.config['dird'], token=token)
        self._disable_service_debug_logs(client)

    def _enable_service_debug_logs(self, client):
        config_patch = [
            {
                'op': 'replace',
                'path': '/debug',
                'value': True,
            }
        ]
        client.config.patch(config_patch)

    def _disable_service_debug_logs(self, client):
        config_patch = [
            {
                'op': 'replace',
                'path': '/debug',
                'value': False,
            }
        ]
        client.config.patch(config_patch)

    def _capture_network_packets(self):
        # udp[12:4]: UDP payload from byte 12, 4 bytes long
        # 0x2112a442: STUN/TURN packet identifier
        stun_filter = 'udp[12:4] = 0x2112a442'
        dns_filter = 'udp port 53'

        filter_ = ' || '.join([stun_filter, dns_filter])

        # -w: Write captured data to pcap file
        # -q: Quiet mode
        # -i: Network interface to listen. any = eth0 (for STUN) + lo (for SIP over WS, decrypted)
        command = [
            'tcpdump',
            '-w',
            f'{self.collection_directory}/network.pcap',
            '-q',
            '-i',
            'any',
            filter_,
        ]
        self.log_processes.append(Popen(command, stderr=PIPE))

    def _capture_sip_rtp_packets(self):
        # -O: Write captured data to pcap file
        # -N: Don't display sngrep interface, just capture
        # -q: Don't print captured dialogs in no interface mode
        # -r: Capture RTP packets payload
        command = [
            'sngrep',
            '-O',
            f'{self.collection_directory}/sngrep.pcap',
            '-N',
            '-q',
            '-r',
        ]
        self.log_processes.append(Popen(command))

    def _enable_agi_debug_mode(self):
        call(['asterisk', '-rx', 'agi set debug on'])

    def _disable_agi_debug_mode(self):
        call(['asterisk', '-rx', 'agi set debug off'])

    def _log_version(self):
        with open('/usr/share/wazo/WAZO-VERSION') as version_file:
            version = version_file.read()
        with open(f'{self.collection_directory}/metadata.txt', 'a') as metadata_file:
            metadata_file.write(f'Wazo version: {version}')

    def _log_start_date(self):
        with open(f'{self.collection_directory}/metadata.txt', 'a') as metadata_file:
            metadata_file.write(f'Start: {self._now()}\n')

    def _log_stop_date(self):
        with open(f'{self.collection_directory}/metadata.txt', 'a') as metadata_file:
            metadata_file.write(f'Stop: {self._now()}\n')

    def _now(self):
        return datetime.datetime.now().astimezone().isoformat()

    def _make_capture_tarball(self, tarball_filename):
        call(['tar', '-C', self.collection_directory, '-czf', tarball_filename, '.'])

    def _clear_directory(self):
        call(['rm', '-rf', self.collection_directory])
