# Example 01 — Hello World

The simplest possible PhantomOrchestra session. No API key required —
the LLM is mocked so this runs entirely offline.

## What It Demonstrates

- Importing and calling `phantom.main.run_task()`
- Mocking the LLM for offline/test usage
- Reading the final `Scene` state and outputs

## Run It

```bash
cd examples/01-hello-world
python main.py
```

Expected output:

```
Final state  : PerformerState.COMPLETE
Iterations   : 2
Budget spent : $0.0000
Task completed successfully.
```

## Use a Real API Key

Remove the `with patch(...)` block in `main.py` and set your key:

```bash
export PHANTOM_API_KEY="your-key-here"
export PHANTOM_MODEL="claude-sonnet-4-6"
python main.py
```
