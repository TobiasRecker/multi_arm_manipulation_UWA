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
import sys
import tempfile
import time
from zoneinfo import ZoneInfo

from agent_trial import Trial
from antigravity_trial_permissions import PYTHON, trace_command


REPO = Path(__file__).resolve().parents[1]
WORKSPACE = REPO.parents[1]
DOCS = REPO / "docs/agent_trials"
DEFAULT_AGY = WORKSPACE / "setup/agent_tools/antigravity/agy"
DEFAULT_MODEL = "gemini-4-hydrogen-high"
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
PROCESS_CONTEXT = (
    DOCS / "PROMPT_HOUSE_DRILL_TRIAL_04.md",
    DOCS / "HOUSE_DRILL_HANDOFF.md",
    DOCS / "house_drill_spec.json",
    REPO / "docs/workpiece_paths.md",
    *CIRCLES_CONTEXT[2:],
)
CASES = {
    "circles": ("box_gemini_20261119", "box-gemini-02", CIRCLES_CONTEXT),
    "nikolaus": ("nikolaus_gemini_20261119", "box-nikolaus-03", HOUSE_CONTEXT),
    "house-drill": ("house_drill_gemini_20261119", "box-house-drill-04", PROCESS_CONTEXT),
}
BASELINE_CONTEXT_FILES = {"AGENTS.md", "box_drawing_pilot.md", "TRACE_PROTOCOL.md", "workpiece_paths.md"}
BOX_FIXTURE = WORKSPACE / "setup/research/offline-carton-sides-20261117/standard/smoothed/result.json"


def perth_time():
    return datetime.now(ZoneInfo("Australia/Perth")).isoformat()


def auto_mode_warning(version):
    # This release rejects Auto while this Linux policy flag is enabled,
    # even when the system Bubblewrap binary works with its own profile.
    if version == "1.5.12" and sys.platform.startswith("linux"):
        policy = Path("/proc/sys/kernel/apparmor_restrict_unprivileged_userns")
        try:
            restricted = policy.read_text().strip() == "1"
        except OSError:
            return None
        if restricted:
            return ("Antigravity CLI 1.5.12 rejects auto mode with "
                    "kernel.apparmor_restrict_unprivileged_userns=1. "
                    "Expect command confirmations. Use --mode=accept-edits to auto-approve file edits.")
    return None


def configure_trial_cli(agent_repo, session, trace):
    # --settings replaces the permissions object for this invocation. Carry
    # over explicit review/deny rules without importing broad global allows.
    user_settings = Path.home() / ".gemini/antigravity-cli/settings.json"
    permissions = json.loads(user_settings.read_text()).get("permissions", {}) if user_settings.exists() else {}
    hooks = agent_repo / ".agents/hooks.json"
    settings = session / "antigravity-settings.json"
    settings.write_text(json.dumps({"permissions": {
        "allow": [f"read_file({BOX_FIXTURE})"],
        "ask": permissions.get("ask", []),
        "deny": [*permissions.get("deny", []), f"write_file({hooks})", f"write_file({settings})"],
    }}, indent=2) + "\n")

    hook = REPO / "tools/antigravity_trial_permissions.py"
    hooks.parent.mkdir(exist_ok=True)
    with hooks.open("x") as stream:
        json.dump({"uwa-trial-permissions": {
            "PreToolUse": [{"matcher": "run_command", "hooks": [{
                "command": shlex.join([PYTHON, "-I", str(hook), str(trace), str(agent_repo)]),
                "timeout": 5,
            }]}],
        }}, stream, indent=2)
        stream.write("\n")
    with (agent_repo / ".git/info/exclude").open("a") as stream:
        stream.write("\n/.agents/hooks.json\n")
    return settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true", help="Save a prompt for a fresh IDE session")
    parser.add_argument("--agy", type=Path, default=DEFAULT_AGY, help="Path to the local Antigravity CLI")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Gemini model slug from agy models (default: {DEFAULT_MODEL})")
    parser.add_argument("--mode", choices=("auto", "accept-edits", "plan"),
                        help="Antigravity execution mode for this CLI session")
    parser.add_argument("--case", choices=CASES, default="circles",
                        help="Task to run in a separate checkout of the current commit")
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
    warning = auto_mode_warning(version) if args.mode == "auto" else None
    if warning:
        print(f"WARNING: {warning}", file=sys.stderr, flush=True)

    folder, task, context = CASES[args.case]
    trial_root = TRIALS / folder
    trial_root.mkdir(parents=True, exist_ok=True)
    session = Path(tempfile.mkdtemp(prefix="session-", dir=trial_root))
    trace = session / "trial"
    agent_repo = session / "repo"
    subprocess.run(["git", "clone", "--quiet", "--no-local", "--single-branch",
                    "--depth", "1", "--no-tags", str(REPO), str(agent_repo)], check=True)
    subprocess.run(["git", "-C", str(agent_repo), "remote", "remove", "origin"], check=True)
    client = "Google Antigravity for VS Code" if args.prepare_only else f"Antigravity CLI {version}"
    settings = None
    if not args.prepare_only and args.mode != "plan":
        settings = configure_trial_cli(agent_repo, session, trace)
        Trial(trace).init(agent_repo, task, f"{client}; model requested: {args.model}")
        (trace / "artifacts").mkdir()
    revision = subprocess.check_output(["git", "-C", str(agent_repo), "rev-parse", "HEAD"], text=True).strip()
    source_prompt = context[0].read_text().rstrip()
    prompt = (f"{source_prompt}\n\n"
              f"Dein Arbeits-Repo ist {agent_repo}.\n"
              f"Dein absoluter Trial-Pfad ist {trace}.\n"
              f"Client laut Start: {client}. Modellvorgabe: {args.model}.\n"
              "Nutze die vorhandenen Tests. Entwickle, ergänze oder ändere keine eigenen Tests.\n")
    finish = shlex.join([PYTHON, str(REPO/'tools/finish_gemini_trial.py'), str(session), 'run01'])
    prompt += ("\nSchließe die Planungsstufe im Logger ab. Für Prüfung und Abgabe führe dann diesen "
               "Aufruf aus und setze bei Bedarf statt run01 den tatsächlichen Ergebnisordnernamen ein.\n"
               f"```bash\n{finish}\n```\n"
               "Der Aufruf protokolliert die Prüfstufe und schließt den Trial bei PASS ab. "
               "Verwende den ausgegebenen Bericht. Bei FAIL lies nur die benannte Fundstelle.\n")
    if settings:
        logger = shlex.join(trace_command(trace))
        prompt += ("\nDer Logger sowie der Ordner trial/artifacts sind bereits vorbereitet. "
                   "Beginne mit diesem Befehl. Nutze denselben absoluten Aufruf für alle Logschritte. "
                   "Protokollschritte separat und ohne Variablen, Umleitungen oder Shellblöcke aufrufen.\n"
                   f"```bash\n{logger} start orient\n"
                   f"{logger} run --label list-files -- /usr/bin/ls -la -- {shlex.quote(str(agent_repo / 'tools'))}\n```\n"
                   "Nutze list_dir zum Lesen von Ordnern. Falls ein eigener Unterordner unter artifacts nötig ist, "
                   "verwende /usr/bin/mkdir -p -- und den wörtlichen absoluten Pfad. "
                   "Der Planer erzeugt seinen Ausgabeordner selbst.\n")
    (session / "prompt.md").write_text(prompt)
    snapshots = session / "context"
    snapshots.mkdir()
    hashes = {}
    for file in context:
        relative = file.relative_to(REPO)
        if file.name in BASELINE_CONTEXT_FILES:
            file = agent_repo / relative
        data = file.read_bytes()
        (snapshots / file.name).write_bytes(data)
        hashes[str(relative)] = hashlib.sha256(data).hexdigest()
    metadata = dict(schema_version=1, case=args.case, repo=str(agent_repo), git_head=revision,
                    trial=str(trace), client=client,
                    model_requested=args.model, mode_requested=args.mode,
                    prepared_at=perth_time(), context_sha256=hashes)
    if warning:
        metadata["auto_mode_warning"] = warning
    if settings:
        metadata.update(antigravity_settings=str(settings), antigravity_log=str(session / "antigravity.log"))
    metadata_path = session / "observer.json"

    def write_metadata():
        temporary = metadata_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(metadata, indent=2) + "\n")
        temporary.replace(metadata_path)

    write_metadata()
    print(f"Session: {session}\nRepo: {agent_repo}\nPrompt: {session / 'prompt.md'}\nTrial: {trace}", flush=True)
    if args.prepare_only:
        return 0

    command = [str(agy), "-i", prompt, "--add-dir", str(session), "--model", args.model]
    if settings:
        command.extend(["--settings", str(settings), "--log-file", metadata["antigravity_log"]])
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
