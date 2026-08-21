from pathlib import Path


WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "ai-task-prioritization.yml"
)


def _run_blocks(text: str) -> list[str]:
    """Return literal YAML run blocks without requiring a YAML dependency."""
    lines = text.splitlines()
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.lstrip()
        if stripped not in {"run: |", "run: |-", "run: |+"}:
            index += 1
            continue

        run_indent = len(line) - len(stripped)
        index += 1
        body: list[str] = []
        while index < len(lines):
            candidate = lines[index]
            if candidate.strip():
                indent = len(candidate) - len(candidate.lstrip())
                if indent <= run_indent:
                    break
            body.append(candidate)
            index += 1
        blocks.append("\n".join(body))
    return blocks


def test_untrusted_github_event_text_never_enters_shell_script_source():
    text = WORKFLOW.read_text(encoding="utf-8")
    run_source = "\n".join(_run_blocks(text))

    # These values are free-form or user-supplied data. GitHub expression
    # substitution inside `run:` happens before the shell parses the script, so
    # quoting the expression in shell syntax does not make it safe. They must be
    # bound through `env:` and referenced only as ordinary shell variables.
    forbidden = (
        "${{ github.event.issue.title }}",
        "${{ join(github.event.issue.labels.*.name, ' ') }}",
        "${{ github.event.inputs.",
    )
    for expression in forbidden:
        assert expression not in run_source, (
            f"untrusted GitHub expression {expression!r} appears in a run block; "
            "pass it through env instead"
        )


def test_security_sensitive_values_are_bound_through_env():
    text = WORKFLOW.read_text(encoding="utf-8")

    expected_bindings = (
        "ISSUE_TITLE: ${{ github.event.issue.title }}",
        "ISSUE_LABELS: ${{ join(github.event.issue.labels.*.name, ' ') }}",
        "TASK_NAME: ${{ github.event.inputs.task_name }}",
    )
    for binding in expected_bindings:
        assert binding in text
