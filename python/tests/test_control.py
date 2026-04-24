from unittest.mock import MagicMock

import pytest

from lite_sdk2 import Configuration, LowCommand
from lite_sdk2.control import cli as control_cli


def test_parse_args_accepts_damping_action():
    args = control_cli.parse_args(["enp2s0", "damping"])
    assert args.action == "damping"
    assert args.nic == "enp2s0"
    assert args.configuration is Configuration.BIMANUAL_ARMS


def test_parse_args_rejects_unknown_action():
    with pytest.raises(SystemExit):
        control_cli.parse_args(["enp2s0", "freestyle"])


def test_parse_configuration_rejects_none():
    with pytest.raises(Exception):
        control_cli._parse_configuration("none")


def test_damping_uses_wait_for_reader_and_streams(monkeypatch):
    fake_pub = MagicMock()
    init = MagicMock()
    pub_factory = MagicMock(return_value=fake_pub)
    monkeypatch.setattr(control_cli, "initialize", init)
    monkeypatch.setattr(control_cli, "publisher", pub_factory)

    call_count = {"n": 0}

    def fake_sleep(_):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise KeyboardInterrupt

    monkeypatch.setattr(control_cli.time, "sleep", fake_sleep)

    result = control_cli.main(
        ["eno1", "damping", "--domain-id", "4", "--disable-retries", "2"]
    )

    assert result == 0
    init.assert_called_once_with(4, network_interface="eno1")
    pub_factory.assert_called_once_with(
        LowCommand, topic="/lowcommand", domain_id=4, network_interface="eno1"
    )
    fake_pub.initialize.assert_called_once()
    fake_pub.wait_for_reader.assert_called_once()
    fake_pub.close.assert_called_once()

    modes_written = [call.args[0].actuator_commands[0].mode for call in fake_pub.write.call_args_list]
    assert modes_written[0] == control_cli.ACTUATOR_MODE_ENABLED
    assert modes_written[-1] == control_cli.ACTUATOR_MODE_DISABLED


def test_disable_sends_disable_commands_only(monkeypatch):
    fake_pub = MagicMock()
    monkeypatch.setattr(control_cli, "initialize", MagicMock())
    monkeypatch.setattr(control_cli, "publisher", MagicMock(return_value=fake_pub))
    monkeypatch.setattr(control_cli.time, "sleep", lambda *_: None)

    result = control_cli.main(
        ["eno1", "disable", "--disable-retries", "3"]
    )

    assert result == 0
    assert fake_pub.write.call_count == 3
    for call in fake_pub.write.call_args_list:
        assert call.args[0].actuator_commands[0].mode == control_cli.ACTUATOR_MODE_DISABLED
    fake_pub.close.assert_called_once()
