from unittest.mock import MagicMock

from lite_sdk2.messages import LowCommand, LowState
from lite_sdk2.monitor import cli as monitor_cli


def test_parse_args_normalizes_hyphenated_aliases():
    args = monitor_cli.parse_args(["enp2s0", "low-state"])
    assert args.monitor == "lowstate"
    assert args.nic == "enp2s0"


def test_lowcommand_resolves_default_topic(monkeypatch):
    fake_sub = MagicMock()
    fake_sub.read.side_effect = KeyboardInterrupt
    init = MagicMock()
    sub_factory = MagicMock(return_value=fake_sub)
    monkeypatch.setattr(monitor_cli, "initialize", init)
    monkeypatch.setattr(monitor_cli, "subscriber", sub_factory)

    result = monitor_cli.main(["enp2s0", "lowcommand", "--domain-id", "7"])

    assert result == 0
    init.assert_called_once_with(7, network_interface="enp2s0")
    sub_factory.assert_called_once_with(
        LowCommand, topic="/lowcommand", domain_id=7, network_interface="enp2s0"
    )
    fake_sub.initialize.assert_called_once()
    fake_sub.close.assert_called_once()


def test_lowstate_resolves_default_topic(monkeypatch):
    fake_sub = MagicMock()
    fake_sub.read.side_effect = KeyboardInterrupt
    sub_factory = MagicMock(return_value=fake_sub)
    monkeypatch.setattr(monitor_cli, "initialize", MagicMock())
    monkeypatch.setattr(monitor_cli, "subscriber", sub_factory)

    monitor_cli.main(["eno1", "lowstate", "--domain-id", "3"])

    sub_factory.assert_called_once_with(
        LowState, topic="/lowstate", domain_id=3, network_interface="eno1"
    )
