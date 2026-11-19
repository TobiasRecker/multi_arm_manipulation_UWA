#!/usr/bin/env python3
"""Approve literal bookkeeping commands for one isolated Antigravity trial."""

import json
from pathlib import Path
import re
import shlex
import sys


LOGGER = Path(__file__).resolve().with_name("agent_trial.py")
PYTHON = "/usr/bin/python3"
TRACE_ACTIONS = {"start", "end", "note", "summary", "finish"}


def trace_command(trial):
    return [PYTHON, "-I", str(LOGGER), "--trial", str(trial)]


def allow_call(call, trial, repo):
    if call.get("name") != "run_command":
        return False
    fields = call.get("args", {})
    if fields.keys() - {"CommandLine", "Cwd", "WaitMsBeforeAsync", "toolSummary"}:
        return False
    if fields.get("Cwd") not in (None, "", str(repo)):
        return False
    command = fields.get("CommandLine")
    if not isinstance(command, str) or any(c in command for c in "\n\r\x00"):
        return False
    try:
        args = shlex.split(command)
    except ValueError:
        return False
    # Requote every argument before comparing. Shell syntax, variable expansion,
    # redirections and chained commands then fail to match the literal command.
    if shlex.join(args) != command:
        return False

    artifacts = trial / "artifacts"
    if args[:3] == ["/usr/bin/mkdir", "-p", "--"] and len(args) == 4:
        directory = Path(args[3])
        return directory.resolve() == directory and (directory == artifacts or (
            directory.parent == artifacts
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,39}", directory.name) is not None
        ))

    prefix = trace_command(trial)
    if args[:len(prefix)] != prefix:
        return False
    rest = args[len(prefix):]
    if rest and rest[0] in TRACE_ACTIONS:
        return True
    # The logger's general `run` subcommand can execute arbitrary code. Only
    # allow this one exact form for listing directories used in the trial.
    if rest[:4] != ["run", "--label", "list-files", "--"]:
        return False
    targets = {str(repo / path) for path in ("tools", "docs", "uwa_cell_tasks/test")}
    targets.update((str(trial), str(artifacts)))
    return (rest[4:7] == ["/usr/bin/ls", "-la", "--"] and len(rest) > 7
            and all(path in targets for path in rest[7:]))


def main():
    trial, repo = map(Path, sys.argv[1:])
    payload = json.load(sys.stdin)
    approved = allow_call(payload.get("toolCall", {}), trial, repo)
    print(json.dumps({"decision": "auto_approve" if approved else "allow"}))


if __name__ == "__main__":
    main()
