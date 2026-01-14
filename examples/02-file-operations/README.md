# Example 02 — File Operations

Demonstrates how PhantomOrchestra handles file write, read, and
verification through the signal pipeline. Uses a scripted LLM so
no API key is needed.

## What It Demonstrates

- `RunCommandDirective` → `CommandOutputReport` round-trip
- Multi-turn conversation flow
- Reading output from the stage workspace

## Run It

```bash
cd examples/02-file-operations
python main.py
```

## Use a Real API Key

```bash
export PHANTOM_API_KEY="your-key"
python main.py
```
