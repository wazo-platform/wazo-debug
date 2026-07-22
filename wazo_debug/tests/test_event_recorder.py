# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from io import StringIO
from unittest import TestCase
from unittest.mock import Mock, patch

from hamcrest import assert_that, contains_string, equal_to, has_entries, has_key, none
from xivo.config_helper import UUIDNotFound

from ..event_recorder import EventRecorder

BUS_CONFIG = {
    'username': 'guest',
    'password': 'guest',
    'host': 'localhost',
    'port': 5672,
    'exchange_name': 'wazo-headers',
    'exchange_type': 'headers',
}


class TestEventRecorderOnMessage(TestCase):
    def setUp(self):
        self.recorder = EventRecorder.from_config(BUS_CONFIG, '/tmp/unused')
        self.buffer = StringIO()
        self.recorder._file = self.buffer

    def _last_record(self):
        return json.loads(self.buffer.getvalue().splitlines()[-1])

    def test_writes_one_json_line_with_full_envelope(self):
        message = Mock(headers={'name': 'call_created', 'origin_uuid': 'the-uuid'})

        self.recorder._on_message({'call_id': '42'}, message)

        record = self._last_record()
        assert_that(
            record,
            has_entries(
                name='call_created',
                headers={'name': 'call_created', 'origin_uuid': 'the-uuid'},
                payload={'call_id': '42'},
            ),
        )
        assert_that(record, has_key('timestamp'))

    def test_message_is_acknowledged(self):
        message = Mock(headers={'name': 'call_created'})

        self.recorder._on_message({}, message)

        message.ack.assert_called_once_with()

    def test_event_count_is_incremented(self):
        message = Mock(headers={'name': 'call_created'})

        self.recorder._on_message({}, message)
        self.recorder._on_message({}, message)

        assert_that(self.recorder.event_count, equal_to(2))

    def test_missing_headers_do_not_raise(self):
        message = Mock(headers=None)

        self.recorder._on_message({'foo': 'bar'}, message)

        record = self._last_record()
        assert_that(record, has_entries(headers={}, payload={'foo': 'bar'}))
        assert_that(record['name'], none())

    def test_non_serializable_values_do_not_crash(self):
        message = Mock(headers={'name': 'weird'})

        self.recorder._on_message({'obj': object()}, message)

        record = self._last_record()
        assert_that(record, has_key('payload'))
        message.ack.assert_called_once_with()

    def test_message_after_file_closed_is_acked_and_dropped(self):
        # After stop() (or a failed stop) closes the file, a late delivery must
        # not crash the consumer callback; it should ack and drop the event.
        self.recorder._file = None
        message = Mock(headers={'name': 'call_created'})

        self.recorder._on_message({'a': 1}, message)

        message.ack.assert_called_once_with()
        assert_that(self.recorder.event_count, equal_to(0))

    def test_each_event_is_a_separate_line(self):
        message = Mock(headers={'name': 'call_created'})

        self.recorder._on_message({'a': 1}, message)
        self.recorder._on_message({'b': 2}, message)

        content = self.buffer.getvalue()
        assert_that(content, contains_string('\n'))
        assert_that(len(content.splitlines()), equal_to(2))


class TestEventRecorderGetConsumers(TestCase):
    def test_binds_exclusive_queue_filtered_on_origin_uuid(self):
        recorder = EventRecorder.from_config(BUS_CONFIG, '/tmp/unused')
        recorder._uuid = 'the-uuid'
        captured = {}

        def fake_consumer(queues, callbacks, auto_declare):
            captured['queues'] = queues
            captured['callbacks'] = callbacks
            return 'consumer'

        result = recorder.get_consumers(fake_consumer, Mock())

        assert_that(result, equal_to(['consumer']))
        assert_that(captured['callbacks'], equal_to([recorder._on_message]))

        queue = captured['queues'][0]
        assert_that(queue.exclusive, equal_to(True))
        binding = list(queue.bindings)[0]
        assert_that(
            binding.arguments,
            has_entries({'origin_uuid': 'the-uuid', 'x-match': 'all'}),
        )


class TestEventRecorderThread(TestCase):
    def test_consumer_thread_is_a_daemon(self):
        # wazo-bus registers a non-daemon consumer thread; the recorder marks it
        # daemon so an interrupted capture cannot block process exit.
        recorder = EventRecorder.from_config(BUS_CONFIG, '/tmp/unused')

        threads = recorder._ThreadableMixin__internal_threads_list
        daemon_flags = [bus_thread.thread.daemon for bus_thread in threads]

        assert_that(daemon_flags, equal_to([True]))


class TestEventRecorderStart(TestCase):
    def test_uuid_is_resolved_and_file_opened(self):
        recorder = EventRecorder.from_config(BUS_CONFIG, '/tmp/unused')
        fake_file = Mock()

        with patch('wazo_debug.event_recorder.get_xivo_uuid', return_value='the-uuid'):
            with patch('builtins.open', return_value=fake_file):
                with patch('wazo_bus.mixins.ThreadableMixin.start') as parent_start:
                    recorder.start()

        parent_start.assert_called_once_with()
        assert_that(recorder._uuid, equal_to('the-uuid'))
        assert_that(recorder.recording, equal_to(True))

    def test_file_is_closed_if_consumer_fails_to_start(self):
        recorder = EventRecorder.from_config(BUS_CONFIG, '/tmp/unused')
        fake_file = Mock()

        with patch('wazo_debug.event_recorder.get_xivo_uuid', return_value='the-uuid'):
            with patch('builtins.open', return_value=fake_file):
                with patch(
                    'wazo_bus.mixins.ThreadableMixin.start',
                    side_effect=RuntimeError('consumer failed'),
                ):
                    self.assertRaises(RuntimeError, recorder.start)

        fake_file.close.assert_called_once_with()
        assert_that(recorder._file, none())

    def test_start_does_nothing_without_uuid(self):
        recorder = EventRecorder.from_config(BUS_CONFIG, '/tmp/unused')

        with patch('wazo_debug.event_recorder.get_xivo_uuid', side_effect=UUIDNotFound):
            with patch('wazo_bus.mixins.ThreadableMixin.start') as parent_start:
                recorder.start()

        parent_start.assert_not_called()
        assert_that(recorder.recording, equal_to(False))


class TestEventRecorderStop(TestCase):
    def test_file_is_closed_even_if_consumer_stop_fails(self):
        recorder = EventRecorder.from_config(BUS_CONFIG, '/tmp/unused')
        fake_file = Mock()
        recorder._file = fake_file

        with patch(
            'wazo_bus.mixins.ThreadableMixin.stop',
            side_effect=RuntimeError('consumer stop failed'),
        ):
            self.assertRaises(RuntimeError, recorder.stop)

        fake_file.close.assert_called_once_with()
        assert_that(recorder._file, none())
