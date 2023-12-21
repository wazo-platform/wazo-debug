# Copyright 2017-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import glob
import logging
import os
import tempfile
from subprocess import call

from cliff.command import Command

logger = logging.getLogger(__name__)


class CollectCommand(Command):
    """Collect information about a Wazo server"""

    def get_parser(self, program_name):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '-o',
            '--output-file',
            action='store',
            help='The path to the output file',
            required=True,
        )
        return parser

    def take_action(self, parsed_args):
        with tempfile.TemporaryDirectory(prefix='wazo-debug-') as temp_directory:
            logger.info('Created temporary directory: "%s"', temp_directory)

            gathering_directory = os.path.join(temp_directory, 'wazo-debug')
            os.mkdir(gathering_directory)

            gather_facts(gathering_directory)
            bundle_facts(temp_directory, parsed_args.output_file)

            logger.info('Removing temporary directory: "%s"', temp_directory)


def gather_facts(gathering_directory):
    logger.info('Gathering facts...')
    gather_log_files(gathering_directory)
    gather_config_files(gathering_directory)
    gather_engine_info(gathering_directory)


def gather_log_files(gathering_directory):
    logger.info('Gathering log files...')

    gathering_log_directory = os.path.join(gathering_directory, 'logs')
    os.mkdir(gathering_log_directory)

    command = (
        ['rsync', '-a']
        + ['--include', 'asterisk/full*']
        + ['--exclude', 'asterisk/*']
        + glob.glob('/var/log/asterisk')
        + glob.glob('/var/log/nginx')
        + glob.glob('/var/log/rabbitmq')
        + glob.glob('/var/log/syslog*')
        + glob.glob('/var/log/wazo-*')
        + glob.glob('/var/log/xivo-*')
        + glob.glob('/var/log/fail2ban*')
        + glob.glob('/var/www/munin')
        + [gathering_log_directory]
    )
    call(command)


def gather_config_files(gathering_directory):
    logger.info('Gathering configuration files...')

    gathering_config_directory = os.path.join(gathering_directory, 'config')
    os.mkdir(gathering_config_directory)

    command = (
        ['rsync', '-a']
        + glob.glob('/etc/wazo-*')
        + glob.glob('/etc/xivo*')
        + glob.glob('/etc/asterisk')
        + glob.glob('/etc/nginx')
        + [gathering_config_directory]
    )
    call(command)


def gather_engine_info(gathering_directory):
    logger.info('Gathering engine information...')

    command = ['rsync', '-a', '/usr/share/wazo/WAZO-VERSION', gathering_directory]
    call(command)

    command = ['timedatectl', 'show']
    with open(f'{gathering_directory}/timedatectl.txt', 'a') as info_file:
        call(command, stdout=info_file)


def bundle_facts(facts_directory, output_file):
    logger.info('Creating tarball...')
    call(['tar', 'caf', output_file, '-C', facts_directory, '.'])
