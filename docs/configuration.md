# Configuration Reference

## How Configuration is Loaded

Settings are resolved in this order (later overrides earlier):

1. Built-in defaults (defined in Pydantic models)
2. `config.toml` file found at the first match of:
   - Path passed to `load_config(path=...)`
   - `$PHANTOM_CONFIG_PATH` environment variable
   - `~/.phantom/config.toml`
   - `./config.toml` in the working directory
3. `PHANTOM_*` environment variables

## TOML File Structure

```toml
[voice]
model = "claude-sonnet-4-6"
api_key = "..."          # prefer env var instead

[voice.fast]             # optional named voice config
model = "claude-haiku-4-5-20251001"

[performer]
enable_terminal = true

[stage]
stage_type = "local"

[orchestra]
max_iterations = 100
```

## VoiceConfig — `[voice]`

| Key | Env Var | Default | Description |
|-----|---------|---------|-------------|
| `model` | `PHANTOM_MODEL` | `claude-sonnet-4-6` | LiteLLM model ID |
| `api_key` | `PHANTOM_API_KEY` | — | Provider API key |
| `base_url` | — | — | Custom API base URL |
| `api_version` | — | — | Azure API version |
| `num_retries` | — | `5` | Retry attempts on failure |
| `retry_min_wait` | — | `8` | Minimum backoff seconds |
| `retry_max_wait` | — | `64` | Maximum backoff seconds |
| `retry_multiplier` | — | `8.0` | Backoff multiplier |
| `temperature` | — | `0.0` | Sampling temperature |
| `top_p` | — | `1.0` | Nucleus sampling threshold |
| `max_input_tokens` | — | — | Cap input token count |
| `max_output_tokens` | — | — | Cap output token count |
| `max_message_chars` | — | `30000` | Truncation threshold |
| `use_prompt_caching` | — | `true` | Enable prompt caching |
| `native_tool_calling` | — | — | Force tool call mode |
| `disable_vision` | — | `false` | Disable image inputs |
| `log_completions` | — | `false` | Log every LLM call |
| `log_completions_folder` | — | `completions` | Log output folder |

### Multiple Voice Configs

Define named configs as TOML subsections. Base `[voice]` values are
inherited unless overridden:

```toml
[voice]
model = "claude-sonnet-4-6"
api_key = "sk-ant-..."

[voice.fast]
model = "claude-haiku-4-5-20251001"
# api_key inherited from [voice]

[voice.openai]
model = "gpt-4o"
api_key = "sk-..."
```

Reference by name in PerformerConfig: `voice_config_name = "fast"`.

## PerformerConfig — `[performer]`

| Key | Default | Description |
|-----|---------|-------------|
| `enable_browsing` | `true` | Allow web browsing directives |
| `enable_file_editor` | `true` | Allow file read/write directives |
| `enable_terminal` | `true` | Allow shell command directives |
| `enable_jupyter` | `false` | Allow notebook cell directives |
| `enable_finish_signal` | `true` | Allow CompleteDirective |
| `enable_stuck_detection` | `true` | Detect and break loops |
| `max_chars_per_observation` | `30000` | Truncate long outputs |
| `system_prompt_template` | `default` | Prompt template name |
| `voice_config_name` | — | Named voice config to use |

## StageConfig — `[stage]`

| Key | Env Var | Default | Description |
|-----|---------|---------|-------------|
| `stage_type` | `PHANTOM_STAGE_TYPE` | `local` | `local` or `docker` |
| `container_image` | — | `ghcr.io/phantom-orchestra/runtime:latest` | Docker image |
| `sandbox_timeout` | — | `120` | Command timeout (seconds) |
| `workspace_dir` | — | temp dir | Workspace path |
| `use_host_network` | — | `false` | Share host network in Docker |
| `max_memory_mb` | — | `4096` | Container memory limit (MB) |
| `env_vars` | — | `{}` | Extra env vars for stage |
| `mount_volumes` | — | `[]` | Docker volume mounts |

### Docker Volume Mounts

```toml
[stage]
stage_type = "docker"
mount_volumes = [
  "/data/input:/workspace/input:ro",
  "/data/output:/workspace/output",
]
```

## OrchestraConfig — `[orchestra]`

| Key | Default | Description |
|-----|---------|-------------|
| `default_voice` | `default` | Named voice config to use |
| `default_performer` | `default` | Default performer class |
| `max_iterations` | `100` | Hard stop on iteration count |
| `max_budget_per_task` | — | USD cost limit per session |
| `file_store_type` | `local` | `local` or `memory` |
| `file_store_path` | `/tmp/phantom/store` | Storage root directory |
| `enable_browser` | `true` | Allow browsing capabilities |
| `workspace_path` | — | Global workspace override |

## Environment Variable Quick Reference

```bash
PHANTOM_API_KEY=sk-ant-...          # LLM API key
PHANTOM_MODEL=claude-sonnet-4-6     # Model ID
PHANTOM_STAGE_TYPE=docker           # local or docker
PHANTOM_LOG_LEVEL=INFO              # DEBUG/INFO/WARNING/ERROR
PHANTOM_CONFIG_PATH=/etc/phantom/config.toml
```
