import logging
import sys
import types

import pytest

import lite_sdk2.channel as channel_module
from lite_sdk2.channel import ChannelSubscriber


class _FakeReader:
    def __init__(self, responses):
        self._responses = list(responses)

    def take(self, N: int = 1):
        if not self._responses:
            return []
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class _FakeDomain:
    calls: list[tuple[int, str | None]] = []

    def __init__(self, domain_id: int, config: str | None = None):
        self.domain_id = domain_id
        self.config = config
        self.__class__.calls.append((domain_id, config))


class _FakeDomainParticipant:
    def __init__(self, domain_id: int):
        self.domain_id = domain_id


class _FakePublisher:
    def __init__(self, participant):
        self.participant = participant


class _FakeSubscriber:
    def __init__(self, participant):
        self.participant = participant


def test_read_waits_for_sample(monkeypatch):
    sub = ChannelSubscriber("rt/test", object)
    sub._reader = _FakeReader([[], ["sample"]])
    monkeypatch.setattr(channel_module.time, "sleep", lambda *_: None)
    assert sub.read() == "sample"


def test_read_ignores_invalid_sample():
    sub = ChannelSubscriber("rt/test", object)
    sub._reader = _FakeReader(
        [ValueError("configuration must be one of: ..."), ["sample"]]
    )
    assert sub.read(timeout=0.01) == "sample"


def test_read_batch_ignores_type_errors():
    sub = ChannelSubscriber("rt/test", object)
    sub._reader = _FakeReader([TypeError("missing field")])
    assert sub.read_batch() == []


def test_read_warns_on_deserialize_error(caplog):
    sub = ChannelSubscriber("rt/test", object)
    sub._reader = _FakeReader([ValueError("oops")])
    with caplog.at_level(logging.WARNING, logger="lite_sdk2.channel"):
        assert sub.read(timeout=0.01) is None
    assert any("Ignoring invalid DDS frame" in record.message for record in caplog.records)


@pytest.fixture
def reset_factory_state():
    saved_factory = channel_module._factory_state
    saved_domain = channel_module._default_domain_id
    saved_nic = channel_module._default_network_interface
    channel_module._factory_state = None
    channel_module._default_domain_id = 0
    channel_module._default_network_interface = None
    _FakeDomain.calls.clear()
    try:
        yield
    finally:
        channel_module._factory_state = saved_factory
        channel_module._default_domain_id = saved_domain
        channel_module._default_network_interface = saved_nic


def test_domain_config_includes_nic(reset_factory_state):
    config = channel_module._build_domain_config(3, "enp2s0")
    assert config is not None
    assert 'name="enp2s0"' in config
    assert 'Id="3"' in config


def test_domain_config_none_for_blank_nic(reset_factory_state):
    assert channel_module._build_domain_config(0, None) is None
    assert channel_module._build_domain_config(0, "") is None


def test_factory_reuses_state_for_same_domain_and_nic(reset_factory_state, monkeypatch):
    fake_pkg = types.ModuleType("cyclonedds")
    fake_pkg.__path__ = []
    fake_domain = types.ModuleType("cyclonedds.domain")
    fake_domain.Domain = _FakeDomain
    fake_domain.DomainParticipant = _FakeDomainParticipant
    fake_pub = types.ModuleType("cyclonedds.pub")
    fake_pub.Publisher = _FakePublisher
    fake_sub = types.ModuleType("cyclonedds.sub")
    fake_sub.Subscriber = _FakeSubscriber

    monkeypatch.setitem(sys.modules, "cyclonedds", fake_pkg)
    monkeypatch.setitem(sys.modules, "cyclonedds.domain", fake_domain)
    monkeypatch.setitem(sys.modules, "cyclonedds.pub", fake_pub)
    monkeypatch.setitem(sys.modules, "cyclonedds.sub", fake_sub)

    a = channel_module._get_factory(3, "enp2s0")
    b = channel_module._get_factory(3, "enp2s0")
    c = channel_module._get_factory(3, "eno1")

    assert a is b
    assert a is not c
    assert len(_FakeDomain.calls) == 2
