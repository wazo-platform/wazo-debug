# Copyright 2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import stun
import textwrap

from cliff.command import Command


class PublicIPCommand(Command):
    "Display the public IPv4 address"

    def get_parser(self, program_name):
        parser = argparse.ArgumentParser(
            prog=program_name,
            description='Detect NAT type and public IP address and port.',
        )
        parser.add_argument(
            '--stun-host',
            action='store',
            required=True,
            help='The hostname of the STUN server to query',
        )
        parser.add_argument(
            '--stun-port',
            action='store',
            type=int,
            help='The port of the STUN server to query',
            default=3478,
        )
        return parser

    def take_action(self, parsed_args):
        print('Detecting NAT type...')
        nat_type, public_ip, public_port = stun.get_ip_info(
            stun_host=parsed_args.stun_host, stun_port=parsed_args.stun_port
        )
        message = textwrap.dedent(
            f'''\
            NAT Type: {nat_type}
            External IP: {public_ip}
            External Port: {public_port}
            '''
        ).strip()
        print(message)
