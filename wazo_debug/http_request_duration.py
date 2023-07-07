# Copyright 2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import logging
import subprocess

from cliff.command import Command

logging.basicConfig()
logger = logging.getLogger(__name__)


class HTTPRequestDurationCommand(Command):
    "Display all HTTP requests sorted by response duration"

    def get_parser(self, program_name):
        parser = argparse.ArgumentParser(
            prog=program_name,
            description='Display HTTP requests sorted by response duration. The first column is the request duration in seconds.',
        )
        parser.add_argument(
            '--access-file',
            action='store',
            required=False,
            default='/var/log/nginx/wazo.access.log',
            help='The Nginx access file to analyze',
        )
        return parser

    def take_action(self, parsed_args):
        print(f'Analyzing log file {parsed_args.access_file}')
        command = (
            f'zcat -f {parsed_args.access_file}'
            ''' | awk -F' ' '{ print $(NF-1) " " $0 }' '''
            ' | grep -v websocket | grep -v asterisk/ws | sort -n '
            ' | less +G'
        )
        try:
            subprocess.run(command, check=True, shell=True)
        except subprocess.CalledProcessError:
            logger.error("Couldn't open the access !")
            exit(2)
