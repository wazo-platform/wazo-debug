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
# Worst-case compressed-to-uncompressed ratio for the output tarball
TARBALL_COMPRESSION_RATIO = 0.80
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

            check_free_space(temp_directory, parsed_args.output_file)

            gathering_directory = os.path.join(temp_directory, 'wazo-debug')
            os.mkdir(gathering_directory)

            gather_facts(gathering_directory)
            bundle_facts(temp_directory, parsed_args.output_file)

            logger.info('Removing temporary directory: "%s"', temp_directory)


def check_free_space(temp_directory, output_file):
    uncompressed_bytes = compute_gathering_size()
    compressed_bytes = int(uncompressed_bytes * TARBALL_COMPRESSION_RATIO)
    output_directory = _existing_ancestor(output_file)

    if _same_filesystem(temp_directory, output_directory):
        # Tarball is built while the uncompressed copy still lives in temp_directory,
        # so both must fit on the shared filesystem at the same time.
        combined_bytes = uncompressed_bytes + compressed_bytes
        if not _has_enough_free_space(temp_directory, combined_bytes):
            raise RuntimeError(
                f'Not enough free space on filesystem hosting "{temp_directory}" '
                f'for uncompressed data + compressed tarball: '
                f'{_format_bytes(shutil.disk_usage(temp_directory).free)} available, '
                f'{_format_bytes(combined_bytes + FREE_SPACE_BUFFER_BYTES)} required.'
            )
        return

    if not _has_enough_free_space(temp_directory, uncompressed_bytes):
        raise RuntimeError(
            f'Not enough free space on filesystem hosting "{temp_directory}" '
            f'for uncompressed data: '
            f'{_format_bytes(shutil.disk_usage(temp_directory).free)} available, '
            f'{_format_bytes(uncompressed_bytes + FREE_SPACE_BUFFER_BYTES)} required.'
        )
    if not _has_enough_free_space(output_directory, compressed_bytes):
        raise RuntimeError(
            f'Not enough free space on filesystem hosting "{output_directory}" '
            f'for compressed tarball: '
            f'{_format_bytes(shutil.disk_usage(output_directory).free)} available, '
            f'{_format_bytes(compressed_bytes + FREE_SPACE_BUFFER_BYTES)} required.'
        )


def _has_enough_free_space(directory, data_bytes):
    free_bytes = shutil.disk_usage(directory).free
    needed_bytes = data_bytes + FREE_SPACE_BUFFER_BYTES
    logger.info(
        'Free space check on "%s": need %s (data %s + buffer %s), have %s',
        directory,
        _format_bytes(needed_bytes),
        _format_bytes(data_bytes),
        _format_bytes(FREE_SPACE_BUFFER_BYTES),
        _format_bytes(free_bytes),
    )
    return free_bytes >= needed_bytes


def _format_bytes(n: int) -> str:
    size = float(n)
    for unit in ('B', 'KiB', 'MiB', 'GiB'):
        if abs(size) < 1024:
            return f'{size:.1f} {unit}'
        size /= 1024
    return f'{size:.1f} TiB'


def _existing_ancestor(path):
    path = os.path.abspath(path)
    while not os.path.exists(path):
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return path


def _same_filesystem(path_a, path_b):
    return os.stat(path_a).st_dev == os.stat(path_b).st_dev


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
