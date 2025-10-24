"""PhantomOrchestra entry point — CLI and programmatic runner."""

import asyncio
import sys

import structlog

from phantom.performer.scene import Scene
from phantom.score.loader import load_config
from phantom.signal.report.control import PerformerState
from phantom.toolkit.logging import configure_logging

__all__ = ["main", "run_task"]

logger = structlog.get_logger(__name__)


async def run_task(
    task: str,
    performer_name: str = "default",
    config_path: str | None = None,
    max_iterations: int = 100,
) -> "Scene":  # type: ignore[name-defined]
    """Run a single task to completion.

    Bootstraps the full signal pipeline, stage, and director for
    a one-shot execution.  Waits for the director to finish and
    tears down the stage before returning.

    Args:
        task: Natural-language description of the task.
        performer_name: Registered performer to instantiate.
        config_path: Optional explicit TOML config path.
        max_iterations: Hard cap on decision steps.

    Returns:
        The final Scene containing state, outputs, and metrics.
    """
    configure_logging()
    config = load_config(config_path)

    import uuid

    from phantom.performer.base import Performer
    from phantom.performer.director import Director
    from phantom.performer.scene import Scene
    from phantom.signal.base import SignalSource
    from phantom.signal.channel import (
        ChannelSubscriber,
        SignalChannel,
    )
    from phantom.signal.depot import SignalDepot
    from phantom.signal.directive.base import Directive
    from phantom.stage.factory import create_stage
    from phantom.vault.factory import create_repository
    from phantom.voice.registry import VoiceRegistry

    session_id = str(uuid.uuid4())

    # Storage layer
    repository = create_repository(
        config.file_store_type,
        config.file_store_path,
    )
    depot = SignalDepot(session_id, repository)
    channel = SignalChannel(session_id, depot)

    # Performer
    voice_registry = VoiceRegistry.from_orchestra_config(config)
    performer = Performer.create(
        performer_name,
        config.primary_performer,
        voice_registry,
    )

    # Scene and stage
    scene = Scene(
        session_id=session_id,
        max_iterations=max_iterations,
    )
    stage = create_stage(config.stage)
    await stage.initialize()

    # Wire stage as directive executor
    async def execute_and_broadcast(
        directive: Directive,
    ) -> None:
        report = await stage.dispatch(directive)
        channel.broadcast(report, SignalSource.ENVIRONMENT)

    def on_directive(signal: object) -> None:
        if isinstance(signal, Directive) and signal.runnable:
            asyncio.create_task(  # noqa: RUF006
                execute_and_broadcast(signal)
            )

    channel.subscribe(
        ChannelSubscriber.STAGE,
        on_directive,  # type: ignore[arg-type]
        "stage_executor",
    )

    director = Director(
        session_id=session_id,
        performer=performer,
        channel=channel,
        scene=scene,
    )

    try:
        scene = await director.start(task)

        # Spin until the director marks execution complete
        while not director.is_complete:
            await asyncio.sleep(0.1)
    finally:
        await stage.teardown()
        channel.close()

    logger.info(
        "task_complete",
        session_id=session_id,
        iterations=scene.iteration,
        state=scene.current_state,
    )

    return scene


def main() -> None:
    """CLI entry point for PhantomOrchestra.

    Subcommands:

    * ``phantom run <task>`` — execute a task and print outputs.
    * ``phantom serve`` — start the FastAPI API server.
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="phantom",
        description="PhantomOrchestra AI task runner",
    )
    subparsers = parser.add_subparsers(dest="command")

    # ------------------------------------------------------------------
    # run subcommand
    # ------------------------------------------------------------------

    run_parser = subparsers.add_parser(
        "run",
        help="Execute a task and wait for completion.",
    )
    run_parser.add_argument(
        "task",
        help="Natural-language task description.",
    )
    run_parser.add_argument(
        "--performer",
        default="default",
        help="Registered performer name to use.",
    )
    run_parser.add_argument(
        "--config",
        default=None,
        help="Path to TOML configuration file.",
    )
    run_parser.add_argument(
        "--max-iterations",
        type=int,
        default=100,
        dest="max_iterations",
        help="Maximum number of decision steps.",
    )

    # ------------------------------------------------------------------
    # serve subcommand
    # ------------------------------------------------------------------

    serve_parser = subparsers.add_parser(
        "serve",
        help="Start the PhantomOrchestra API server.",
    )
    serve_parser.add_argument(
        "--host",
        default="0.0.0.0",  # noqa: S104
        help="Bind address (default: 0.0.0.0).",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port to listen on (default: 3000).",
    )
    serve_parser.add_argument(
        "--config",
        default=None,
        help="Path to TOML configuration file.",
    )

    args = parser.parse_args()

    if args.command == "run":
        scene = asyncio.run(
            run_task(
                task=args.task,
                performer_name=args.performer,
                config_path=args.config,
                max_iterations=args.max_iterations,
            )
        )
        if scene.current_state == PerformerState.COMPLETE:
            print("Task completed successfully.")
            for key, value in scene.outputs.items():
                print(f"{key}: {value}")
        else:
            print(
                f"Task ended with state: {scene.current_state}",
                file=sys.stderr,
            )
            sys.exit(1)

    elif args.command == "serve":
        import uvicorn

        from phantom.conductor.app import create_app

        app = create_app(args.config)
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_config=None,
        )

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
