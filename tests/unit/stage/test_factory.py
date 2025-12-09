"""Tests for stage factory."""

import pytest

from phantom.score.stage_config import StageConfig
from phantom.stage.container_stage import ContainerStage
from phantom.stage.factory import create_stage
from phantom.stage.local_stage import LocalStage


class TestCreateStage:
    def test_local_type_returns_local_stage(self, tmp_path):
        cfg = StageConfig(stage_type="local", workspace_dir=str(tmp_path))
        stage = create_stage(cfg)
        assert isinstance(stage, LocalStage)

    def test_docker_type_returns_container_stage(self):
        cfg = StageConfig(stage_type="docker")
        stage = create_stage(cfg)
        assert isinstance(stage, ContainerStage)

    def test_unknown_type_raises_value_error(self):
        cfg = StageConfig(stage_type="local")  # valid to construct
        cfg.stage_type = "kubernetes"  # patch to invalid
        with pytest.raises(ValueError, match="Unknown stage type"):
            create_stage(cfg)
