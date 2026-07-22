# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import logging
from datetime import datetime, timezone

import kombu
from wazo_bus.consumer import BusConsumer
from xivo.config_helper import UUIDNotFound, get_xivo_uuid

logger = logging.getLogger(__name__)


class EventRecorder(BusConsumer):
    """Record events published on the Wazo bus to a JSON Lines file."""

    def __init__(self, output_file, **bus_config):
        super().__init__(name='wazo-debug', **bus_config)
        # mark bus consumer threads as daemon to avoid blocking process shutdown
        bus_threads = getattr(self, '_ThreadableMixin__internal_threads_list', [])
        for bus_thread in bus_threads:
            bus_thread.thread.daemon = True
        self._output_file = output_file
        self._uuid = None
        self._file = None
        self.event_count = 0

    @classmethod
    def from_config(cls, bus_config, output_file):
        return cls(output_file, **bus_config)

    @property
    def recording(self):
        return self._file is not None

    def start(self):
        try:
            self._uuid = get_xivo_uuid(logger)
        except UUIDNotFound:
            logger.error('XIVO_UUID is not set; bus events will not be recorded')
            return
        self._file = open(self._output_file, 'a')
        try:
            super().start()
        except Exception:
            self._file.close()
            self._file = None
            raise

    def stop(self):
        try:
            super().stop()
        finally:
            if self._file is not None:
                self._file.close()
                self._file = None

    def get_consumers(self, Consumer, channel):
        queue = kombu.Queue(
            exchange=self._exchange,
            exclusive=True,
            auto_delete=True,
            durable=False,
            bindings=[
                kombu.binding(
                    self._exchange,
                    arguments={'origin_uuid': self._uuid, 'x-match': 'all'},
                )
            ],
        )
        self._exchange.bind(channel).declare()
        return [
            Consumer(queues=[queue], callbacks=[self._on_message], auto_declare=True)
        ]

    def _on_message(self, body, message):
        # A late delivery once the file is closed (e.g. during stop) is dropped,
        # but still acked so the consumer does not get stuck redelivering it.
        if self._file is None:
            message.ack()
            return
        headers = message.headers or {}
        record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'name': headers.get('name'),
            'headers': headers,
            'payload': body,
        }
        try:
            line = json.dumps(record, default=str)
            self._file.write(line + '\n')
            self._file.flush()
            self.event_count += 1
        except (TypeError, ValueError):
            logger.exception('Could not serialize bus event %r', headers.get('name'))
        finally:
            message.ack()
