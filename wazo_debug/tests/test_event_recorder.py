# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from io import StringIO
from unittest import TestCase
from unittest.mock import Mock, mock_open, patch

from hamcrest import assert_that, contains_string, equal_to, has_entries, has_key, none

from ..event_recorder import EventRecorder, find_xivo_uuid

BUS_CONFIG = {
    'username': 'guest',
    'password': 'guest',
    'host': 'localhost',
    'port': 5672,
    'exchange_name': 'wazo-headers',
    'exchange_type': 'headers',
}


class TestFindXivoUUID(TestCase):
    def test_config_value_takes_precedence(self):
        with patch.dict('os.environ', {'XIVO_UUID': 'from-env'}):
            result = find_xivo_uuid('from-config')

        assert_that(result, equal_to('from-config'))

    def test_environment_used_when_no_config_value(self):
        with patch.dict('os.environ', {'XIVO_UUID': 'from-env'}):
            result = find_xivo_uuid()

        assert_that(result, equal_to('from-env'))

    def test_file_used_when_no_config_or_environment(self):
        contents = 'export XIVO_UUID=from-file\n'
        with patch.dict('os.environ', {}, clear=True):
            with patch('builtins.open', mock_open(read_data=contents)):
                result = find_xivo_uuid()

        assert_that(result, equal_to('from-file'))

    def test_file_value_is_unquoted(self):
        contents = 'export XIVO_UUID="quoted-uuid"\n'
        with patch.dict('os.environ', {}, clear=True):
            with patch('builtins.open', mock_open(read_data=contents)):
                result = find_xivo_uuid()

        assert_that(result, equal_to('quoted-uuid'))

    def test_none_when_nothing_available(self):
        with patch.dict('os.environ', {}, clear=True):
            with patch('builtins.open', side_effect=OSError):
                result = find_xivo_uuid()

        assert_that(result, none())


class TestEventRecorderOnMessage(TestCase):
    def setUp(self):
        self.recorder = EventRecorder(BUS_CONFIG, '/tmp/unused', uuid='the-uuid')
        self.buffer = StringIO()
        self.recorder._file = self.buffer

    def _last_record(self):
        return json.loads(self.buffer.getvalue().splitlines()[-1])

    def test_writes_one_json_line_with_expected_fields(self):
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

    def test_each_event_is_a_separate_line(self):
        message = Mock(headers={'name': 'call_created'})

        self.recorder._on_message({'a': 1}, message)
        self.recorder._on_message({'b': 2}, message)

        content = self.buffer.getvalue()
        assert_that(content, contains_string('\n'))
        assert_that(len(content.splitlines()), equal_to(2))


class TestEventRecorderStartWithoutUUID(TestCase):
    def test_start_does_nothing_without_uuid(self):
        # No config uuid, no XIVO_UUID env, no uuid file -> uuid is None
        with patch.dict('os.environ', {}, clear=True):
            with patch('builtins.open', side_effect=OSError):
                recorder = EventRecorder(BUS_CONFIG, '/tmp/unused', uuid=None)

        assert_that(recorder._uuid, none())

        with patch('kombu.Connection') as connection:
            recorder.start()

        connection.assert_not_called()
        assert_that(recorder._thread, none())
        assert_that(recorder.recording, equal_to(False))
