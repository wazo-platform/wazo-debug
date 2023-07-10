#!/usr/bin/env python3
# Copyright 2017-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from setuptools import setup
from setuptools import find_packages


setup(
    name='wazo-debug',
    version='1.1',
    author='Wazo Authors',
    author_email='dev@wazo.community',
    url='http://wazo.community',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'wazo-debug = wazo_debug.main:main',
        ],
        'wazo_debug.commands': [
            'access = wazo_debug.access:AccessCommand',
            'capture = wazo_debug.capture:CaptureCommand',
            'collect = wazo_debug.collect:CollectCommand',
            'public-ip = wazo_debug.public_ip:PublicIPCommand',
            'http-request-duration = wazo_debug.http_request_duration:HTTPRequestDurationCommand',
        ],
    },
)
