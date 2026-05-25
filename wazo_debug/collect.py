# Copyright 2017-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import fnmatch
import glob
import logging
import os
import shutil
import tempfile
from subprocess import call

from cliff.command import Command

logger = logging.getLogger(__name__)

FREE_SPACE_BUFFER_BYTES = 500 * 1024 * 1024  # 500 MB safety buffer
ASTERISK_LOG_DIR = '/var/log/asterisk'


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

            check_free_space(temp_directory)

            gathering_directory = os.path.join(temp_directory, 'wazo-debug')
            os.mkdir(gathering_directory)

            gather_facts(gathering_directory)
            bundle_facts(temp_directory, parsed_args.output_file)

            logger.info('Removing temporary directory: "%s"', temp_directory)


def check_free_space(target_directory):
    required_bytes = compute_gathering_size()
    free_bytes = shutil.disk_usage(target_directory).free
    needed_bytes = required_bytes + FREE_SPACE_BUFFER_BYTES
    logger.info(
        'Estimated gathered data size: %d bytes; free space on "%s": %d bytes',
        required_bytes,
        target_directory,
        free_bytes,
    )
    if free_bytes < needed_bytes:
        raise RuntimeError(
            f'Not enough free space on filesystem hosting "{target_directory}": '
            f'{free_bytes} bytes available, but {needed_bytes} bytes are required '
            f'({required_bytes} bytes of data + {FREE_SPACE_BUFFER_BYTES} bytes buffer).'
        )


def compute_gathering_size():
    paths = _log_source_paths() + _config_source_paths() + _engine_info_source_paths()
    return sum(_path_size(p) for p in paths)


def _log_source_paths():
    return (
        glob.glob('/var/log/asterisk')
        + glob.glob('/var/log/nginx')
        + glob.glob('/var/log/rabbitmq')
        + glob.glob('/var/log/syslog*')
        + glob.glob('/var/log/wazo-*')
        + glob.glob('/var/log/xivo-*')
        + glob.glob('/var/log/fail2ban*')
        + glob.glob('/var/www/munin')
    )


def _config_source_paths():
    return (
        glob.glob('/etc/wazo-*')
        + glob.glob('/etc/xivo*')
        + glob.glob('/etc/asterisk')
        + glob.glob('/etc/nginx')
    )


def _engine_info_source_paths():
    return glob.glob('/usr/share/wazo/WAZO-VERSION')


def _path_size(path):
    if os.path.islink(path):
        return 0
    if os.path.isfile(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return 0
    if not os.path.isdir(path):
        return 0

    is_asterisk_log_dir = path == ASTERISK_LOG_DIR
    total = 0
    for root, dirs, files in os.walk(path):
        if is_asterisk_log_dir and root != path:
            # rsync filter excludes asterisk subdirectories (only keeps full* at top level)
            dirs[:] = []
            continue
        for name in files:
            if is_asterisk_log_dir and not fnmatch.fnmatch(name, 'full*'):
                continue
            full = os.path.join(root, name)
            if os.path.islink(full):
                continue
            try:
                total += os.path.getsize(full)
            except OSError:
                continue
    return total


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
        + _log_source_paths()
        + [gathering_log_directory]
    )
    call(command)


def gather_config_files(gathering_directory):
    logger.info('Gathering configuration files...')

    gathering_config_directory = os.path.join(gathering_directory, 'config')
    os.mkdir(gathering_config_directory)

    command = ['rsync', '-a'] + _config_source_paths() + [gathering_config_directory]
    call(command)


def gather_engine_info(gathering_directory):
    logger.info('Gathering engine information...')

    command = ['rsync', '-a'] + _engine_info_source_paths() + [gathering_directory]
    call(command)

    command = ['timedatectl', 'show']
    with open(f'{gathering_directory}/timedatectl.txt', 'a') as info_file:
        call(command, stdout=info_file)


def bundle_facts(facts_directory, output_file):
    logger.info('Creating tarball...')
    call(['tar', 'caf', output_file, '-C', facts_directory, '.'])
