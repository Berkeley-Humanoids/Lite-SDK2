import logging
import sys
import time
from dataclasses import dataclass
from threading import Event, Lock, Thread
from typing import Any, Callable, Generic, TypeVar

from .topics import default_topic, ros_topic_to_dds

MessageT = TypeVar("MessageT")

_LOGGER = logging.getLogger(__name__)

# Library code must not scribble on stdout unconfigured, but DDS deserialization
# warnings are genuinely useful to see out of the box. Attach a stderr handler
# (once) if the consumer hasn't configured `lite_sdk2.channel` logging yet.
if not _LOGGER.handlers and not logging.getLogger().handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    _LOGGER.addHandler(_handler)
    _LOGGER.setLevel(logging.WARNING)


@dataclass(slots=True)
class _FactoryState:
    domain_id: int
    network_interface: str | None
    domain: Any | None
    participant: Any
    publisher: Any
    subscriber: Any


_factory_lock = Lock()
_factory_state: _FactoryState | None = None
_default_domain_id = 0
_default_network_interface: str | None = None


def initialize(domain_id: int = 0, network_interface: str | None = None) -> None:
    """Bind the process-wide DDS participant to a domain and NIC.

    Must be called once before constructing publishers or subscribers. Calling
    again with different arguments tears down and rebuilds the participant.
    """
    global _default_domain_id, _default_network_interface
    _default_domain_id = domain_id
    _default_network_interface = _strip(network_interface)
    _get_factory(domain_id, _default_network_interface)


def publisher(
    message_type: type[MessageT],
    *,
    topic: str | None = None,
    domain_id: int | None = None,
    network_interface: str | None = None,
) -> "ChannelPublisher[MessageT]":
    resolved = topic if topic is not None else default_topic(message_type)
    return ChannelPublisher(resolved, message_type, domain_id, network_interface)


def subscriber(
    message_type: type[MessageT],
    *,
    topic: str | None = None,
    domain_id: int | None = None,
    network_interface: str | None = None,
) -> "ChannelSubscriber[MessageT]":
    resolved = topic if topic is not None else default_topic(message_type)
    return ChannelSubscriber(resolved, message_type, domain_id, network_interface)


class ChannelPublisher(Generic[MessageT]):
    """DDS publisher for a single topic.

    ``topic`` accepts either a ROS-style name ("/lowcommand", "lowcommand") or
    an already-prefixed DDS name ("rt/lowcommand"); both resolve to the same
    wire topic. Public attribute ``topic_name`` stores the final DDS name.
    """

    def __init__(
        self,
        topic: str,
        message_type: type[MessageT],
        domain_id: int | None = None,
        network_interface: str | None = None,
    ):
        self.topic_name = ros_topic_to_dds(topic)
        self.message_type = message_type
        self.domain_id = domain_id
        self.network_interface = _strip(network_interface)
        self._factory: _FactoryState | None = None
        self._topic: Any | None = None
        self._writer: Any | None = None

    def initialize(self) -> None:
        from cyclonedds.pub import DataWriter
        from cyclonedds.topic import Topic

        self._factory = _get_factory(self.domain_id, self.network_interface)
        self._topic = Topic(self._factory.participant, self.topic_name, self.message_type)
        self._writer = DataWriter(self._factory.publisher, self._topic)

    def write(self, message: MessageT) -> None:
        """Realtime-safe write. Does not wait for readers to be matched."""
        if self._writer is None:
            raise RuntimeError("ChannelPublisher.initialize() must be called before write().")
        self._writer.write(message)

    def wait_for_reader(self, timeout: float) -> bool:
        """Poll until at least one matching reader exists, or timeout. Not realtime-safe."""
        if self._writer is None:
            raise RuntimeError("ChannelPublisher.initialize() must be called before wait_for_reader().")
        deadline = time.monotonic() + timeout
        while not self._has_matching_reader():
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.01)
        return True

    def _has_matching_reader(self) -> bool:
        status = getattr(self._writer, "publication_matched_status", None)
        if status is not None and hasattr(status, "current_count"):
            return status.current_count > 0
        matched = getattr(self._writer, "matched_subscriptions", None)
        return bool(matched) if matched is not None else True

    def close(self) -> None:
        self._writer = None
        self._topic = None


class ChannelSubscriber(Generic[MessageT]):
    """DDS subscriber for a single topic.

    ``topic`` accepts either a ROS-style name ("/lowstate", "lowstate") or an
    already-prefixed DDS name ("rt/lowstate"); both resolve to the same wire
    topic. Public attribute ``topic_name`` stores the final DDS name.
    """

    def __init__(
        self,
        topic: str,
        message_type: type[MessageT],
        domain_id: int | None = None,
        network_interface: str | None = None,
    ):
        self.topic_name = ros_topic_to_dds(topic)
        self.message_type = message_type
        self.domain_id = domain_id
        self.network_interface = _strip(network_interface)
        self._factory: _FactoryState | None = None
        self._topic: Any | None = None
        self._reader: Any | None = None
        self._callback_thread: Thread | None = None
        self._callback_stop = Event()

    def initialize(
        self,
        callback: Callable[[MessageT], None] | None = None,
        poll_period: float = 0.01,
    ) -> None:
        from cyclonedds.sub import DataReader
        from cyclonedds.topic import Topic

        self._factory = _get_factory(self.domain_id, self.network_interface)
        self._topic = Topic(self._factory.participant, self.topic_name, self.message_type)
        self._reader = DataReader(self._factory.subscriber, self._topic)

        if callback is not None:
            self._callback_stop.clear()

            def _worker() -> None:
                while not self._callback_stop.is_set():
                    sample = self.read(timeout=poll_period)
                    if sample is not None:
                        callback(sample)

            self._callback_thread = Thread(target=_worker, daemon=True)
            self._callback_thread.start()

    def read(self, timeout: float | None = None) -> MessageT | None:
        if self._reader is None:
            raise RuntimeError("ChannelSubscriber.initialize() must be called before read().")

        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            samples = self._take(max_samples=1)
            if samples:
                return samples[-1]
            if deadline is not None and time.monotonic() >= deadline:
                return None
            time.sleep(0.001)

    def read_batch(self, max_samples: int = 1) -> list[MessageT]:
        if self._reader is None:
            raise RuntimeError("ChannelSubscriber.initialize() must be called before read_batch().")
        return self._take(max_samples=max_samples)

    def _take(self, max_samples: int) -> list[MessageT]:
        try:
            return list(self._reader.take(N=max_samples))
        except (TypeError, ValueError) as exc:
            _LOGGER.warning("Ignoring invalid DDS frame on topic '%s': %s", self.topic_name, exc)
            return []

    def close(self) -> None:
        self._callback_stop.set()
        if self._callback_thread is not None:
            self._callback_thread.join(timeout=1.0)
        self._callback_thread = None
        self._reader = None
        self._topic = None


def _strip(value: str | None) -> str | None:
    return None if value is None else value.strip() or None


def _get_factory(domain_id: int | None, network_interface: str | None) -> _FactoryState:
    global _factory_state

    resolved_domain = _default_domain_id if domain_id is None else domain_id
    resolved_nic = _default_network_interface if network_interface is None else network_interface
    resolved_nic = _strip(resolved_nic)

    with _factory_lock:
        if (
            _factory_state is None
            or _factory_state.domain_id != resolved_domain
            or _factory_state.network_interface != resolved_nic
        ):
            from cyclonedds.domain import Domain, DomainParticipant
            from cyclonedds.pub import Publisher
            from cyclonedds.sub import Subscriber

            config = _build_domain_config(resolved_domain, resolved_nic)
            domain = None if config is None else Domain(resolved_domain, config)
            participant = DomainParticipant(resolved_domain)
            _factory_state = _FactoryState(
                domain_id=resolved_domain,
                network_interface=resolved_nic,
                domain=domain,
                participant=participant,
                publisher=Publisher(participant),
                subscriber=Subscriber(participant),
            )
        return _factory_state


def _build_domain_config(domain_id: int, network_interface: str | None) -> str | None:
    if not network_interface:
        return None
    return (
        '<?xml version="1.0" encoding="UTF-8" ?>'
        f'<CycloneDDS><Domain Id="{int(domain_id)}"><General><Interfaces>'
        f'<NetworkInterface name="{network_interface}" priority="default" multicast="default" />'
        "</Interfaces></General></Domain></CycloneDDS>"
    )
