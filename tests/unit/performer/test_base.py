"""Tests for the Performer registry."""

import pytest

from phantom.performer.base import Performer
from phantom.performer.scene import Scene
from phantom.score.performer_config import PerformerConfig
from phantom.score.voice_config import VoiceConfig
from phantom.signal.directive.base import Directive
from phantom.signal.directive.control import NoOpDirective
from phantom.voice.registry import VoiceRegistry

# ---------------------------------------------------------------------------
# Concrete test double — minimal implementation of Performer
# ---------------------------------------------------------------------------


class _EchoPerformer(Performer):
    """Trivial Performer that always emits a NoOpDirective."""

    def decide(self, scene: Scene) -> Directive:
        return NoOpDirective()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def voice_registry():
    return VoiceRegistry(
        configs={"default": VoiceConfig()},
        default_name="default",
    )


@pytest.fixture
def performer_config():
    return PerformerConfig()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPerformerRegistry:
    def setup_method(self):
        """Ensure test registrations don't leak across tests."""
        # Save registry state and restore after each test
        self._orig = dict(Performer._registry)

    def teardown_method(self):
        Performer._registry.clear()
        Performer._registry.update(self._orig)

    def test_register_and_get_class_works(self):
        Performer.register("_Echo", _EchoPerformer)
        cls = Performer.get_class("_Echo")
        assert cls is _EchoPerformer

    def test_get_class_raises_value_error_for_unknown_name(self):
        with pytest.raises(ValueError, match="Unknown performer"):
            Performer.get_class("nonexistent-performer")

    def test_create_instantiates_registered_performer(
        self, performer_config, voice_registry
    ):
        Performer.register("_Echo", _EchoPerformer)
        instance = Performer.create(
            "_Echo",
            config=performer_config,
            voice_registry=voice_registry,
        )
        assert isinstance(instance, _EchoPerformer)

    def test_create_raises_for_unknown_name(
        self, performer_config, voice_registry
    ):
        with pytest.raises(ValueError, match="Unknown performer"):
            Performer.create(
                "ghost-performer",
                config=performer_config,
                voice_registry=voice_registry,
            )


class TestPerformerInterface:
    def test_decide_returns_directive(self, performer_config, voice_registry):
        p = _EchoPerformer(
            config=performer_config,
            voice_registry=voice_registry,
        )
        scene = Scene(session_id="t")
        directive = p.decide(scene)
        assert isinstance(directive, Directive)

    def test_complete_defaults_to_false(
        self, performer_config, voice_registry
    ):
        p = _EchoPerformer(
            config=performer_config,
            voice_registry=voice_registry,
        )
        assert p.complete is False

    def test_complete_setter(self, performer_config, voice_registry):
        p = _EchoPerformer(
            config=performer_config,
            voice_registry=voice_registry,
        )
        p.complete = True
        assert p.complete is True

    def test_name_returns_class_name(self, performer_config, voice_registry):
        p = _EchoPerformer(
            config=performer_config,
            voice_registry=voice_registry,
        )
        assert p.name == "_EchoPerformer"

    def test_get_available_tools_returns_empty_list_by_default(
        self, performer_config, voice_registry
    ):
        p = _EchoPerformer(
            config=performer_config,
            voice_registry=voice_registry,
        )
        assert p.get_available_tools() == []

    def test_build_system_prompt_returns_empty_string_by_default(
        self, performer_config, voice_registry
    ):
        p = _EchoPerformer(
            config=performer_config,
            voice_registry=voice_registry,
        )
        assert p.build_system_prompt() == ""
