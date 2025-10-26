"""Shared pytest fixtures for PhantomOrchestra test suite."""

import pytest

from phantom.score.orchestra_config import OrchestraConfig
from phantom.score.voice_config import VoiceConfig
from phantom.signal.channel import SignalChannel
from phantom.signal.depot import SignalDepot
from phantom.vault.local_vault import LocalRepository
from phantom.vault.memory_vault import MemoryRepository


@pytest.fixture
def temp_dir(tmp_path):
    """Return a temporary directory Path for tests."""
    return tmp_path


@pytest.fixture
def memory_repository():
    """Return a fresh MemoryRepository instance."""
    return MemoryRepository()


@pytest.fixture
def local_repository(tmp_path):
    """Return a LocalRepository rooted at a temp directory."""
    return LocalRepository(str(tmp_path / "vault"))


@pytest.fixture
def sample_voice_config():
    """Return a VoiceConfig with a fake API key for testing."""
    return VoiceConfig(
        model="gpt-4o",
        api_key="sk-fake-key-for-testing",  # type: ignore[arg-type]
    )


@pytest.fixture
def sample_orchestra_config(sample_voice_config):
    """Return an OrchestraConfig suitable for unit tests."""
    return OrchestraConfig(
        voices={"default": sample_voice_config},
        file_store_type="memory",
    )


@pytest.fixture
def signal_depot(memory_repository):
    """Return a SignalDepot backed by MemoryRepository."""
    return SignalDepot(
        session_id="test-session",
        repository=memory_repository,
    )


@pytest.fixture
def signal_channel(signal_depot):
    """Return a SignalChannel using the shared test depot."""
    channel = SignalChannel(
        session_id="test-session",
        depot=signal_depot,
    )
    yield channel
    channel.close()
