# Copyright 2017-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import glob
import logging
import os
import tempfile

from cliff.command import Command
from subprocess import call

logger = logging.getLogger(__name__)


class CollectCommand(Command):
    "Collect informations about a Wazo server"

    def get_parser(self, program_name):
        parser = argparse.ArgumentParser()
        parser.add_argument('-o', '--output-file', action='store', help='The path to the output file', required=True)
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


def gather_log_files(gathering_directory):
    logger.info('Gathering log files...')

    gathering_log_directory = os.path.join(gathering_directory, 'logs')
    os.mkdir(gathering_log_directory)

    command = (
        ['rsync', '-a'] +
        glob.glob('/var/log/wazo-*') +
        glob.glob('/var/log/xivo-*') +
        [gathering_log_directory]
    )
    call(command)


def bundle_facts(facts_directory, output_file):
    logger.info('Creating tarball...')
    call(['tar', 'caf', output_file, '-C', facts_directory, '.'])


if __name__ == '__main__':
    main()
