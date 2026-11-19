#!/usr/bin/env python3
"""Prepare a fresh compatibility trial and optionally capture its terminal."""

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time
from zoneinfo import ZoneInfo


REPO = Path(__file__).resolve().parents[1]
WORKSPACE = REPO.parents[1]
DOCS = REPO / "docs/agent_trials"
DEFAULT_AGY = WORKSPACE / "setup/agent_tools/antigravity/agy"
TRIALS = WORKSPACE / "setup/agent_trials"
CIRCLES_CONTEXT = (
    DOCS / "PROMPT_GEMINI_TRIAL_02.md",
    DOCS / "GEMINI_HANDOFF.md",
    DOCS / "TRACE_PROTOCOL.md",
    REPO / "docs/box_drawing_pilot.md",
    REPO / "AGENTS.md",
    REPO / "tools/start_gemini_trial.py",
)
HOUSE_CONTEXT = (
    DOCS / "PROMPT_NIKOLAUS_TRIAL_03.md",
    DOCS / "NIKOLAUS_HANDOFF.md",
    *CIRCLES_CONTEXT[2:],
)


def perth_time():
    return datetime.now(ZoneInfo("Australia/Perth")).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true", help="Save a prompt for a fresh IDE session")
    parser.add_argument("--agy", type=Path, default=DEFAULT_AGY, help="Path to the local Antigravity CLI")
    parser.add_argument("--model", help="Gemini model slug from agy models")
    parser.add_argument("--mode", choices=("auto", "accept-edits", "plan"),
                        help="Antigravity execution mode for this CLI session")
    parser.add_argument("--case", choices=("circles", "nikolaus"), default="circles",
                        help="The Nikolaus test opens a separate checkout of the current commit")
    args = parser.parse_args()
    if args.prepare_only and args.mode:
        parser.error("--mode applies to CLI sessions; choose the mode in the IDE for --prepare-only")

    version = None
    agy = args.agy.expanduser().resolve()
    if not args.prepare_only:
        if not os.isatty(0) or not os.isatty(1):
            parser.error("Start in an interactive terminal, or use --prepare-only for the IDE")
        if shutil.which("script") is None or not os.access(agy, os.X_OK):
            parser.error("Requires script (util-linux) and the local Antigravity CLI")
        try:
            version = subprocess.run([agy, "--version"], check=True, capture_output=True,
                                     text=True, timeout=15).stdout.strip()
        except (OSError, subprocess.SubprocessError) as error:
            parser.error(f"Antigravity version check failed: {error}")

    house = args.case == "nikolaus"
    trial_root = TRIALS / ("nikolaus_gemini_20261119" if house else "box_gemini_20261119")
    trial_root.mkdir(parents=True, exist_ok=True)
    session = Path(tempfile.mkdtemp(prefix="session-", dir=trial_root))
    trace = session / "trial"
    agent_repo = REPO
    if house:
        agent_repo = session / "repo"
        subprocess.run(["git", "clone", "--quiet", "--no-local", "--single-branch",
                        "--depth", "1", "--no-tags", str(REPO), str(agent_repo)], check=True)
        subprocess.run(["git", "-C", str(agent_repo), "remote", "remove", "origin"], check=True)
    revision = subprocess.check_output(["git", "-C", str(agent_repo), "rev-parse", "HEAD"], text=True).strip()
    context = HOUSE_CONTEXT if house else CIRCLES_CONTEXT
    source_prompt = context[0].read_text().rstrip()
    client = "Google Antigravity for VS Code" if args.prepare_only else f"Antigravity CLI {version}"
    prompt = (f"{source_prompt}\n\n"
              f"Dein Arbeits-Repo ist {agent_repo}.\n"
              f"Dein absoluter Trial-Pfad ist {trace}.\n"
              f"Client laut Start: {client}. Modellvorgabe: {args.model or 'keine, tatsächliches Modell erfassen falls sichtbar'}.\n")
    (session / "prompt.md").write_text(prompt)
    snapshots = session / "context"
    snapshots.mkdir()
    hashes = {}
    for file in context:
        relative = file.relative_to(REPO)
        if house and file.name in ("AGENTS.md", "box_drawing_pilot.md", "TRACE_PROTOCOL.md"):
            file = agent_repo / relative
        data = file.read_bytes()
        (snapshots / file.name).write_bytes(data)
        hashes[str(relative)] = hashlib.sha256(data).hexdigest()
    metadata = dict(schema_version=1, case=args.case, repo=str(agent_repo), git_head=revision,
                    trial=str(trace), client=client,
                    model_requested=args.model, mode_requested=args.mode,
                    prepared_at=perth_time(), context_sha256=hashes)
    metadata_path = session / "observer.json"

    def write_metadata():
        temporary = metadata_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(metadata, indent=2) + "\n")
        temporary.replace(metadata_path)

    write_metadata()
    print(f"Session: {session}\nRepo: {agent_repo}\nPrompt: {session / 'prompt.md'}\nTrial: {trace}", flush=True)
    if args.prepare_only:
        return 0

    command = [str(agy), "-i", prompt]
    if house:
        command.extend(["--add-dir", str(session)])
    if args.model:
        command.extend(["--model", args.model])
    if args.mode:
        command.append(f"--mode={args.mode}")
    metadata["terminal_started_at"] = perth_time()
    write_metadata()
    begin = time.monotonic()
    code = None
    try:
        code = subprocess.run(["script", "-qef", "-O", str(session / "terminal.log"),
                               "-T", str(session / "terminal.timing"),
                               "-c", shlex.join(command)], cwd=agent_repo).returncode
        return code if code >= 0 else 128 - code
    finally:
        metadata.update(terminal_ended_at=perth_time(), terminal_wall_s=time.monotonic()-begin,
                        terminal_exit_code=code)
        write_metadata()


if __name__ == "__main__":
    raise SystemExit(main())
