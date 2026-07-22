# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase
from unittest.mock import Mock, patch

from hamcrest import assert_that, equal_to, none

from ..capture import CaptureCommand, TokenCreationError


class TestRecordBusEvents(TestCase):
    def _command(self):
        command = CaptureCommand(Mock(), Mock())
        command.app.config = {'bus': {}, 'uuid': None}
        return command

    def test_recorder_setup_failure_does_not_abort_capture(self):
        command = self._command()

        with patch(
            'wazo_debug.capture.EventRecorder.from_config',
            side_effect=RuntimeError('bus init failed'),
        ):
            command._record_bus_events()  # must not raise

        assert_that(command.event_recorder, none())

    def test_recorder_is_started_on_success(self):
        command = self._command()
        recorder = Mock()

        with patch(
            'wazo_debug.capture.EventRecorder.from_config', return_value=recorder
        ):
            command._record_bus_events()

        recorder.start.assert_called_once_with()
        assert_that(command.event_recorder, equal_to(recorder))


class TestCaptureTeardown(TestCase):
    def _command(self):
        command = CaptureCommand(Mock(), Mock())
        command.app.config = {'bus': {}, 'uuid': None}
        return command

    def test_stop_capture_runs_even_when_start_fails(self):
        command = self._command()

        with patch.object(command, '_start_capture', side_effect=RuntimeError('boom')):
            with patch.object(command, '_stop_capture') as stop_capture:
                self.assertRaises(RuntimeError, command.take_action, Mock())

        stop_capture.assert_called_once_with()

    def test_stop_capture_survives_a_failing_recorder_stop(self):
        command = self._command()
        command.log_processes = []
        recorder = Mock(recording=True)
        recorder.stop.side_effect = RuntimeError('bus down')
        command.event_recorder = recorder

        with patch.multiple(
            command,
            _log_stop_date=Mock(),
            _create_token=Mock(side_effect=TokenCreationError('no token')),
            _disable_agi_debug_mode=Mock(),
            _make_capture_tarball=Mock(),
            _clear_directory=Mock(),
        ):
            command._stop_capture()  # must not raise

            # Teardown continued past the failing recorder.
            command._make_capture_tarball.assert_called_once()
            command._clear_directory.assert_called_once()
