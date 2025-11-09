"""Tests for SignalChannel."""

from phantom.signal.base import SignalSource
from phantom.signal.channel import ChannelSubscriber, SignalChannel
from phantom.signal.depot import SignalDepot
from phantom.signal.directive.terminal import RunCommandDirective
from phantom.vault.memory_vault import MemoryRepository


def _channel() -> SignalChannel:
    repo = MemoryRepository()
    depot = SignalDepot(session_id="ch-test", repository=repo)
    return SignalChannel(session_id="ch-test", depot=depot)


class TestSignalChannelSubscription:
    def test_subscribing_and_receiving_broadcasted_signal(self):
        ch = _channel()
        received: list = []
        ch.subscribe(
            ChannelSubscriber.TEST,
            lambda s: received.append(s),
            "cb1",
        )
        sig = RunCommandDirective(command="echo test")
        ch.broadcast(sig, source=SignalSource.PERFORMER)
        ch.close()
        assert len(received) == 1

    def test_unsubscribing_stops_signal_delivery(self):
        ch = _channel()
        received: list = []
        ch.subscribe(
            ChannelSubscriber.TEST,
            lambda s: received.append(s),
            "cb2",
        )
        ch.unsubscribe(ChannelSubscriber.TEST, "cb2")
        sig = RunCommandDirective(command="echo removed")
        ch.broadcast(sig, source=SignalSource.PERFORMER)
        ch.close()
        assert len(received) == 0

    def test_multiple_subscribers_all_receive_signal(self):
        ch = _channel()
        bucket_a: list = []
        bucket_b: list = []
        ch.subscribe(
            ChannelSubscriber.DIRECTOR,
            lambda s: bucket_a.append(s),
            "dir-cb",
        )
        ch.subscribe(
            ChannelSubscriber.STAGE,
            lambda s: bucket_b.append(s),
            "stage-cb",
        )
        sig = RunCommandDirective(command="ls")
        ch.broadcast(sig, source=SignalSource.PERFORMER)
        ch.close()
        assert len(bucket_a) == 1
        assert len(bucket_b) == 1


class TestSignalChannelBroadcast:
    def test_broadcast_assigns_id_and_timestamp(self):
        ch = _channel()
        sig = RunCommandDirective(command="date")
        ch.broadcast(sig, source=SignalSource.PERFORMER)
        ch.close()
        assert sig.id >= 0
        assert sig.timestamp != ""

    def test_broadcast_assigns_source(self):
        ch = _channel()
        sig = RunCommandDirective(command="whoami")
        ch.broadcast(sig, source=SignalSource.USER)
        ch.close()
        assert sig.source == SignalSource.USER

    def test_broadcast_assigns_incrementing_ids(self):
        ch = _channel()
        sigs = [RunCommandDirective(command=f"cmd-{i}") for i in range(3)]
        for s in sigs:
            ch.broadcast(s, source=SignalSource.PERFORMER)
        ch.close()
        ids = [s.id for s in sigs]
        assert ids == sorted(ids)
        assert len(set(ids)) == 3  # all unique

    def test_broadcast_on_closed_channel_is_ignored(self):
        ch = _channel()
        ch.close()
        sig = RunCommandDirective(command="never-runs")
        # Should not raise; signal id remains INVALID
        ch.broadcast(sig, source=SignalSource.PERFORMER)
        assert sig.id == -1


class TestSignalChannelSecretMasking:
    def test_secret_replaced_with_redacted_in_string_field(self):
        ch = _channel()
        ch.mask_secrets({"supersecret": "my-api-key"})

        received: list = []
        ch.subscribe(
            ChannelSubscriber.TEST,
            lambda s: received.append(s),
            "mask-cb",
        )

        # command field contains the secret
        sig = RunCommandDirective(command="token=supersecret")
        ch.broadcast(sig, source=SignalSource.PERFORMER)
        ch.close()

        assert len(received) == 1
        masked_cmd = received[0].command
        assert "supersecret" not in masked_cmd
        assert "<REDACTED>" in masked_cmd

    def test_empty_secret_not_registered(self):
        ch = _channel()
        ch.mask_secrets({"": "empty"})
        # Empty string should not be in the secrets table
        with ch._lock:
            assert "" not in ch._secrets
        ch.close()


class TestSignalChannelReplay:
    def test_replay_returns_committed_signals(self):
        ch = _channel()
        for i in range(3):
            sig = RunCommandDirective(command=f"replay-{i}")
            ch.broadcast(sig, source=SignalSource.PERFORMER)
        ch.close()

        replayed = ch.replay(start_id=0)
        assert len(replayed) == 3

    def test_replay_respects_id_bounds(self):
        ch = _channel()
        for i in range(5):
            sig = RunCommandDirective(command=f"r-{i}")
            ch.broadcast(sig, source=SignalSource.PERFORMER)
        ch.close()

        replayed = ch.replay(start_id=1, end_id=3)
        assert len(replayed) == 3
