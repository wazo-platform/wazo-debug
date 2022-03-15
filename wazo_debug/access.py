# Copyright 2017-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import logging
import random
import time
import subprocess

from cliff.command import Command

logging.basicConfig()
logger = logging.getLogger(__name__)

ssh_max_retries = 3


class AccessCommand(Command):
    """Open an access to this Platform even behind a NAT or a Firewall.
    This is done opening a SSH tunnel on a remote server, the local port being exposed on a random port on the remote server.
    """

    def get_parser(self, program_name):
        parser = argparse.ArgumentParser(
            prog=program_name,
            description='Open an access to this Platform even behind a NAT or a Firewall.',
        )
        parser.add_argument(
            '-l',
            '--local-port',
            action='store',
            help='The local port being exposed. Default to SSH port tcp/22.',
            default=22,
        )
        parser.add_argument(
            '-s',
            '--remote-server',
            action='store',
            required=True,
            help='The remote server where the tunnel will be opened.',
        )
        parser.add_argument(
            '-r',
            '--remote-server-port',
            action='store',
            required=True,
            help='The remote server port.',
        )
        parser.add_argument(
            '-u',
            '--remote-user',
            action='store',
            required=True,
            help='The unix user on the remote server.',
        )
        parser.add_argument(
            '-i',
            '--identity',
            action='store',
            required=True,
            help="The remote user's SSH private key file.",
        )
        parser.add_argument(
            '-t',
            '--timeout',
            action='store',
            type=int,
            help='The tunnel will timeout after this much seconds. Defaults to 8 hours.',
            default=28800,
        )
        return parser

    def take_action(self, parsed_args):
        self.check_access(parsed_args)

        # We need a retry mechanism just in case there's a port collision on
        # the remote server, in which case we make a new attempt with a different
        # random port
        for attempt in range(ssh_max_retries):
            result = self.open_access(parsed_args)
            if result == 0:
                break
        else:
            logger.critical('Max retries (%s) exceeded, exiting.', ssh_max_retries)
            exit(1)

    def check_access(self, parsed_args):
        ssh_command = [
            'ssh',
            '-o',
            'StrictHostKeyChecking=no',
            '-o',
            'PreferredAuthentications=publickey',
            '-o',
            'ExitOnForwardFailure=yes',
            '-o',
            'ServerAliveInterval=15',
            '-o',
            'ServerAliveCountMax=10',
            '-o',
            'ControlMaster=no',
            '-o',
            'ConnectTimeout=2',
            '-l',
            parsed_args.remote_user,
            '-p',
            str(parsed_args.remote_server_port),
            '-i',
            parsed_args.identity,
            parsed_args.remote_server,
            'exit 0',
        ]
        logger.debug(
            f'''\
Opening the access using this command:
    {' '.join(ssh_command)}'''
        )
        logger.info('Checking connectivity...')
        try:
            subprocess.run(ssh_command, check=True)
        except subprocess.CalledProcessError:
            logger.error("Couldn't open the access !")
            exit(1)
        except KeyboardInterrupt:
            logger.debug('KeyboardInterrupt (CTRL-C)')

    def open_access(self, parsed_args):
        remote_port = random.randint(22022, 22222)

        ssh_command = [
            'ssh',
            '-o',
            'StrictHostKeyChecking=no',
            '-o',
            'PreferredAuthentications=publickey',
            '-o',
            'ExitOnForwardFailure=yes',
            '-o',
            'ServerAliveInterval=15',
            '-o',
            'ServerAliveCountMax=10',
            '-o',
            'ControlMaster=no',
            '-l',
            parsed_args.remote_user,
            '-p',
            str(parsed_args.remote_server_port),
            '-i',
            parsed_args.identity,
            '-R',
            f'0.0.0.0:{remote_port}:localhost:{parsed_args.local_port}',
            '-N',
            parsed_args.remote_server,
        ]
        full_command = [
            'timeout',
            '--foreground',
            str(parsed_args.timeout),
        ] + ssh_command

        human_readable_timeout = time.strftime(
            "%H:%M:%S", time.gmtime(parsed_args.timeout)
        )

        logger.debug(
            f'''\
Opening the access using this command:
    {' '.join(full_command)}'''
        )

        logger.info(
            f'''\
Access will open now. To connect as the 'root' user on the current server, one can use the following command:

    ssh root@{parsed_args.remote_server} -p {remote_port}

Keep the terminal open and it'll last for {human_readable_timeout}. Close the terminal or hit Ctrl-C to cut it.'''
        )
        try:
            subprocess.run(full_command, check=True)
        except subprocess.CalledProcessError as e:
            logger.error("Couldn't open the access !")
            logger.debug('stdout: %s', e.stdout)
            logger.error('stderr: %s', e.stderr)
            return e.returncode
        except KeyboardInterrupt:
            logger.debug('KeyboardInterrupt (CTRL-C)')

        return 0
