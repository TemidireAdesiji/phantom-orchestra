# Example 03 — Custom Performer

Demonstrates how to create a rule-based Performer that never calls
an LLM. `DiagnosticsPerformer` follows a deterministic script of
shell commands and completes when the list is exhausted.

## What It Demonstrates

- Subclassing `Performer` and implementing `decide()`
- Registering a custom performer with `Performer.register()`
- Selecting a performer by name in `run_task()`
- A performer that requires no LLM at all

## Run It

```bash
cd examples/03-custom-performer
python main.py
```

No API key needed — this performer is fully deterministic.

## Extending This Pattern

Replace the `STEPS` list with logic that reads the `scene` to
make dynamic decisions based on prior observations:

```python
def decide(self, scene: Scene) -> Directive:
    last_report = scene.reports[-1] if scene.reports else None
    if last_report and "error" in last_report.content.lower():
        return RunCommandDirective(command="echo 'fixing error...'")
    ...
```
