"""CodeAct performer: executes tasks via code and tool calls."""

import re
from typing import Any

import structlog

from phantom.performer.base import Performer
from phantom.performer.scene import Scene
from phantom.score.performer_config import PerformerConfig
from phantom.signal.directive.base import Directive
from phantom.signal.directive.control import (
    CompleteDirective,
    NoOpDirective,
)
from phantom.signal.directive.filesystem import (
    EditFileDirective,
    ReadFileDirective,
    WriteFileDirective,
)
from phantom.signal.directive.message import MessageDirective
from phantom.signal.directive.terminal import (
    RunCommandDirective,
    RunNotebookDirective,
)
from phantom.voice.message import Message, ToolCall
from phantom.voice.registry import VoiceRegistry

__all__ = ["CodeActPerformer"]

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT_TEMPLATE = (
    "You are PhantomOrchestra, an expert AI assistant "
    "that solves tasks autonomously using code and tools.\n\n"
    "You have access to the following tools:\n"
    "{tool_descriptions}\n\n"
    "## Guidelines\n"
    "- Think step-by-step before acting\n"
    "- Prefer running code to verify assumptions\n"
    "- When you have completed the task, call the finish tool\n"
    "- If you cannot complete a task, explain why clearly\n\n"
    "## Environment\n"
    "- You have access to a Linux terminal with bash\n"
    "- You can read and write files in the workspace\n"
    "- Python 3.11+ is available\n\n"
    "Workspace directory: {workspace_dir}\n"
)


class CodeActPerformer(Performer):
    """Performer that uses code execution to solve tasks.

    Implements the CodeAct paradigm: the agent reasons about tasks
    and executes code to interact with the environment, iteratively
    refining its approach based on observations.

    Args:
        config: PerformerConfig with capability toggles and prompt
            settings.
        voice_registry: Registry of available LLM providers.
        workspace_dir: Path used in the system prompt to orient the
            agent about where files reside.
    """

    def __init__(
        self,
        config: PerformerConfig,
        voice_registry: VoiceRegistry,
        workspace_dir: str = "/workspace",
    ) -> None:
        super().__init__(config, voice_registry)
        self._workspace_dir = workspace_dir

    # ------------------------------------------------------------------
    # Core decision loop
    # ------------------------------------------------------------------

    def decide(self, scene: Scene) -> Directive:
        """Call LLM with current history and parse response.

        Builds the full message list (system + history), submits it to
        the LLM, appends the response to scene history, updates cost
        metrics, then converts the response to a Directive.

        Args:
            scene: Current session state.

        Returns:
            Next Directive for the Stage to execute.
        """
        voice = self._voice_registry.get(self._config.voice_config_name)

        messages = self._build_messages(scene)
        tools = self.get_available_tools()

        logger.info(
            "calling_llm",
            model=voice.model,
            iteration=scene.iteration,
            history_length=len(scene.history),
            num_tools=len(tools),
        )

        response = voice.complete(
            messages=messages,
            tools=tools if tools else None,
        )

        # Sync cost into scene budget tracker
        scene.update_metrics(voice.cumulative_metrics)

        # Persist assistant response in history
        scene.history.append(response)

        return self._parse_response_to_directive(response)

    # ------------------------------------------------------------------
    # Message construction
    # ------------------------------------------------------------------

    def _build_messages(self, scene: Scene) -> list[Message]:
        """Combine the system prompt with scene conversation history.

        The system message is always prepended as the first message.

        Args:
            scene: Current session state.

        Returns:
            Full ordered list of messages for the LLM call.
        """
        system_msg = Message.system(self.build_system_prompt())
        return [system_msg, *list(scene.history)]

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response_to_directive(
        self,
        response: Message,
    ) -> Directive:
        """Convert an LLM response Message into a Directive.

        Priority order:
        1. Tool calls (structured JSON from function calling).
        2. Fenced bash code blocks (```bash ... ```).
        3. Fenced python code blocks (```python ... ```).
        4. Completion phrases in plain text.
        5. Default: MessageDirective waiting for user response.

        Args:
            response: Assistant Message from the LLM.

        Returns:
            The most appropriate Directive subclass instance.
        """
        if response.tool_calls:
            return self._tool_call_to_directive(response.tool_calls[0])

        content: str = response.content or ""  # type: ignore[assignment]

        bash_match = re.search(
            r"```bash\n(.*?)\n```",
            content,
            re.DOTALL,
        )
        if bash_match:
            return RunCommandDirective(
                command=bash_match.group(1).strip(),
                thought=content[:200],
            )

        python_match = re.search(
            r"```python\n(.*?)\n```",
            content,
            re.DOTALL,
        )
        if python_match:
            return RunNotebookDirective(
                code=python_match.group(1).strip(),
                thought=content[:200],
            )

        lower = content.lower()
        completion_phrases = (
            "task complete",
            "i have completed",
            "finished the task",
            "task is complete",
            "successfully completed",
        )
        if any(phrase in lower for phrase in completion_phrases):
            return CompleteDirective(thought=content[:200])

        return MessageDirective(
            content=content,
            wait_for_response=True,
        )

    def _tool_call_to_directive(
        self,
        tool_call: ToolCall,
    ) -> Directive:
        """Convert an LLM tool call into the matching Directive.

        Uses a dispatch table keyed by tool name.  Unknown tool names
        produce a warning log and a :class:`NoOpDirective`.

        Args:
            tool_call: The first (or only) tool call from the LLM.

        Returns:
            Concrete Directive subclass matching the tool name.
        """
        name = tool_call.name
        args = tool_call.arguments

        dispatch: dict[str, Any] = {
            "run_bash": lambda a: RunCommandDirective(
                command=a.get("command", ""),
                cwd=a.get("cwd"),
            ),
            "run_python": lambda a: RunNotebookDirective(
                code=a.get("code", ""),
            ),
            "read_file": lambda a: ReadFileDirective(
                path=a.get("path", ""),
                start_line=a.get("start_line", 0),
                end_line=a.get("end_line", -1),
            ),
            "write_file": lambda a: WriteFileDirective(
                path=a.get("path", ""),
                content=a.get("content", ""),
            ),
            "edit_file": lambda a: EditFileDirective(
                path=a.get("path", ""),
                command=a.get("command", "str_replace"),
                old_str=a.get("old_str"),
                new_str=a.get("new_str"),
                file_text=a.get("file_text"),
            ),
            "finish": lambda a: CompleteDirective(
                outputs=a.get("outputs", {}),
            ),
        }

        if name not in dispatch:
            logger.warning(
                "unknown_tool_call",
                tool_name=name,
                provider=self.name,
            )
            return NoOpDirective()

        return dispatch[name](args)  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # Tool definitions
    # ------------------------------------------------------------------

    def get_available_tools(self) -> list[dict]:
        """Build OpenAI-format tool definitions based on config flags.

        Returns:
            List of tool definition dicts for litellm.
        """
        tools: list[dict] = []

        if self._config.enable_terminal:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "run_bash",
                        "description": (
                            "Execute a bash command in the sandbox"
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "command": {
                                    "type": "string",
                                    "description": ("Bash command to execute"),
                                },
                                "cwd": {
                                    "type": "string",
                                    "description": (
                                        "Working directory override"
                                    ),
                                },
                            },
                            "required": ["command"],
                        },
                    },
                }
            )

        if self._config.enable_jupyter:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "run_python",
                        "description": (
                            "Execute Python code in a Jupyter kernel"
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "code": {
                                    "type": "string",
                                    "description": (
                                        "Python source code to execute"
                                    ),
                                },
                            },
                            "required": ["code"],
                        },
                    },
                }
            )

        if self._config.enable_file_editor:
            tools.extend(self._file_tools())

        if self._config.enable_finish_signal:
            tools.append(self._finish_tool())

        return tools

    def _file_tools(self) -> list[dict]:
        """Return file operation tool definitions.

        Returns:
            List containing read_file, write_file, edit_file schemas.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": (
                        "Read the contents of a file in the workspace"
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": (
                                    "Absolute or relative file path"
                                ),
                            },
                            "start_line": {
                                "type": "integer",
                                "description": (
                                    "First line to read (0-indexed)"
                                ),
                                "default": 0,
                            },
                            "end_line": {
                                "type": "integer",
                                "description": (
                                    "Last line to read (-1 = EOF)"
                                ),
                                "default": -1,
                            },
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": (
                        "Create or overwrite a file with new content"
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Target file path",
                            },
                            "content": {
                                "type": "string",
                                "description": ("Full text content to write"),
                            },
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": (
                        "Perform a structured edit on an existing file"
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Target file path",
                            },
                            "command": {
                                "type": "string",
                                "description": (
                                    "Edit command: view, create, "
                                    "str_replace, or insert"
                                ),
                                "enum": [
                                    "view",
                                    "create",
                                    "str_replace",
                                    "insert",
                                ],
                            },
                            "old_str": {
                                "type": "string",
                                "description": (
                                    "Text to replace (for str_replace)"
                                ),
                            },
                            "new_str": {
                                "type": "string",
                                "description": (
                                    "Replacement text (for str_replace)"
                                ),
                            },
                            "file_text": {
                                "type": "string",
                                "description": (
                                    "Full file content (for create)"
                                ),
                            },
                            "insert_line": {
                                "type": "integer",
                                "description": (
                                    "Line after which to insert (for insert)"
                                ),
                            },
                        },
                        "required": ["path", "command"],
                    },
                },
            },
        ]

    def _finish_tool(self) -> dict:
        """Return the finish tool definition.

        Returns:
            Tool dict for signalling task completion with outputs.
        """
        return {
            "type": "function",
            "function": {
                "name": "finish",
                "description": (
                    "Signal that the task is complete and provide "
                    "named output artefacts"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "outputs": {
                            "type": "object",
                            "description": (
                                "Key-value map of named output "
                                "artefacts, e.g. "
                                '{"result": "...", '
                                '"summary": "..."}'
                            ),
                            "additionalProperties": {"type": "string"},
                        },
                    },
                    "required": [],
                },
            },
        }

    def build_system_prompt(self) -> str:
        """Build the system prompt from the template.

        Returns:
            Formatted system prompt string.
        """
        tools = self.get_available_tools()
        tool_descriptions = "\n".join(
            "- {name}: {desc}".format(
                name=t["function"]["name"],
                desc=t["function"]["description"],
            )
            for t in tools
        )
        return SYSTEM_PROMPT_TEMPLATE.format(
            tool_descriptions=tool_descriptions,
            workspace_dir=self._workspace_dir,
        )


# Register this performer under its class name and as the default
Performer.register("CodeActPerformer", CodeActPerformer)
Performer.register("default", CodeActPerformer)
