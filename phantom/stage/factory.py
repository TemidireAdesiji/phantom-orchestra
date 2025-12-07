"""Stage factory for PhantomOrchestra."""

from phantom.score.stage_config import StageConfig
from phantom.stage.base import Stage

__all__ = ["create_stage"]


def create_stage(config: StageConfig) -> Stage:
    """Instantiate the appropriate Stage implementation.

    Selects between :class:`~phantom.stage.local_stage.LocalStage`
    and :class:`~phantom.stage.container_stage.ContainerStage`
    based on ``config.stage_type``.

    Args:
        config: Stage configuration including ``stage_type``.

    Returns:
        An uninitialised Stage instance ready for
        :meth:`~phantom.stage.base.Stage.initialize`.

    Raises:
        ValueError: When ``config.stage_type`` is not one of
            ``'docker'`` or ``'local'``.
    """
    from phantom.stage.container_stage import ContainerStage
    from phantom.stage.local_stage import LocalStage

    if config.stage_type == "docker":
        return ContainerStage(config)
    if config.stage_type == "local":
        return LocalStage(config)
    raise ValueError(
        f"Unknown stage type: {config.stage_type!r}. "
        "Valid options: 'docker', 'local'"
    )
