# Copyright 2021-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.chain_map import ChainMap
from xivo.config_helper import (
    parse_config_dir,
    parse_config_file,
    read_config_file_hierarchy,
)

_APP_NAME = 'wazo-debug'
_DEFAULT_CONFIG = {
    'config_file': f'/etc/{_APP_NAME}/config.yml',
    'extra_config_files': f'/etc/{_APP_NAME}/conf.d/',
    'auth': {
        'host': 'localhost',
        'port': 9497,
        'prefix': None,
        'https': False,
        'key_file': '/var/lib/wazo-auth-keys/wazo-debug-key.yml',
    },
    'calld': {
        'host': 'localhost',
        'port': '9500',
        'prefix': None,
        'https': False,
    },
    'call-logd': {
        'host': 'localhost',
        'port': '9298',
        'prefix': None,
        'https': False,
    },
    'webhookd': {
        'host': 'localhost',
        'port': '9300',
        'prefix': None,
        'https': False,
    },
    'amid': {
        'host': 'localhost',
        'port': '9491',
        'prefix': None,
        'https': False,
    },
    'dird': {
        'host': 'localhost',
        'port': '9489',
        'prefix': None,
        'https': False,
    },
    'chatd': {
        'host': 'localhost',
        'port': '9304',
        'prefix': None,
        'https': False,
    },
}


def build(parsed_args):
    user_file_config = _read_user_config(parsed_args)
    system_file_config = read_config_file_hierarchy(
        ChainMap(user_file_config, _DEFAULT_CONFIG)
    )
    service_key_file = _load_key_file(
        ChainMap(user_file_config, system_file_config, _DEFAULT_CONFIG)
    )
    final_config = ChainMap(
        user_file_config, service_key_file, system_file_config, _DEFAULT_CONFIG
    )
    return final_config


def _read_user_config(parsed_args):
    if not parsed_args.config:
        return {}
    configs = parse_config_dir(parsed_args.config)
    return ChainMap(*configs)


def _load_key_file(config):
    key_file = parse_config_file(config['auth']['key_file'])
    return {
        'auth': {
            'username': key_file['service_id'],
            'password': key_file['service_key'],
        }
    }
