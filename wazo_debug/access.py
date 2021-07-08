# Copyright 2017-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import logging
import random
import time
from subprocess import call
from cliff.command import Command

logger = logging.getLogger(__name__)


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
            help='The remote server where the tunnel will be opened. Default to Wazo\' Support access server.',
            default='support-access.wazo.io',
        )
        parser.add_argument(
            '-r',
            '--remote-server-port',
            action='store',
            help='The remote server port.',
            default=22000,
        )
        parser.add_argument(
            '-u',
            '--remote-user',
            action='store',
            help='The unix user on the remote server.',
            default='customer',
        )
        parser.add_argument(
            '-p',
            '--remote-password',
            action='store',
            help="The remote user's password.",
            default='dA24zoB5anPj2JBcAn86bTVCCWSjhN4JDsKPyD7JaFuopvxHupWKMLk7kPQHmsPSMAjonKiBStyRQ99fEEoSixzuCUBywhrcg7dDQvFot9cSWo7PimTM9BbS9vq49ATe',
        )
        parser.add_argument(
            '-t',
            '--timeout',
            action='store',
            help='The tunnel will timeout after this much seconds. Default to 8 hours.',
            default=28800,
        )
        return parser

    def take_action(self, parsed_args):

        # We need a retry mechanism just in case there's a port collision on the remote server, in which case we make a new attempt with a different random port
        attempt = 1
        max_retries = 3
        result = -1
        while result != 0:
            if attempt > max_retries:
                logger.critical(f'Max retries ({max_retries}) exceeded, exiting.')
                exit(1)

            result = self.open_access(parsed_args)

    def open_access(self, parsed_args):
        remote_port = random.randint(22022, 22222)

        ssh_command = f'ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=10 -o ControlMaster=no {parsed_args.remote_user}@{parsed_args.remote_server} -p {parsed_args.remote_server_port} -R0.0.0.0:{remote_port}:localhost:{parsed_args.local_port} sleep infinity'

        full_command = f"timeout {parsed_args.timeout} sshpass -e {ssh_command}"

        human_readable_timeout = time.strftime(
            "%H:%M:%S", time.gmtime(parsed_args.timeout)
        )

        logger.info(
            f'''Access will open now. To connect as the 'root' user on the current server, one can use the following command:

    ssh root@{parsed_args.remote_server} -p {remote_port}

Keep the terminal open and it''ll last for {human_readable_timeout}. Close the terminal or hit Ctrl-C to cut it.'''
        )

        logger.debug(
            f'''Opening the access using this command:
    {full_command}'''
        )

        result = call(
            full_command.split(' '), env={'SSHPASS': parsed_args.remote_password}
        )

        if result != 0:
            logger.error("Couldn't open the access !")

        return result
