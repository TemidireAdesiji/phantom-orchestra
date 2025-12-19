"""Performer (agent) module for PhantomOrchestra.

Contains the abstract Performer base class, the Director controller
that drives performers through their execution loop, the Scene state
container, PerformerState enum, and the CodeActPerformer concrete
implementation.

Import the main classes from here rather than from internal submodules.

Exported names:
    Performer       -- abstract base; subclass to build custom agents.
    Director        -- async controller that runs the agent loop.
    Scene           -- mutable state container for a session.
    PerformerState  -- enum of lifecycle states (LOADING, RUNNING, …).
    CodeActPerformer -- default agent using code execution and tools.
"""

from phantom.performer.base import Performer

# codeact module registers CodeActPerformer in Performer._registry
# as a side effect of import; it must be imported before any code
# that calls Performer.create("default", ...).
from phantom.performer.codeact import CodeActPerformer
from phantom.performer.director import Director
from phantom.performer.scene import Scene
from phantom.signal.report.control import PerformerState

__all__ = [
    "CodeActPerformer",
    "Director",
    "Performer",
    "PerformerState",
    "Scene",
]
