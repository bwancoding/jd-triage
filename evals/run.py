#!/usr/bin/env python3
"""
jd-triage eval harness — layer 1 (consistency) and layer 2 (rule compliance).

Neither layer needs a human-labelled "correct" verdict. Layer 1 asks whether the
skill returns the same answer twice; layer 2 asks whether it followed its own
stated rules. Both are mechanically checkable, and between them they catch the
failure modes that matter: an ambiguous spec the model resolves at random, and a
selling-point rule that quietly never fires.

Every run happens in a throwaway sandbox with its own copy of the skill and its
own workspace. The real ~/.claude/jd-triage is never touched — the harness
verifies that before it exits.

    ./run.py                        all cases, 3 runs each
    ./run.py --only 01a 07a         just those cases
    ./run.py --runs 5 --jobs 6      more repetitions, more parallelism
    ./run.py --model sonnet

Stdlib only, no dependencies.
"""

import argparse
import concurrent.futures
import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent
SRC = REPO / "src"
CASES_DIR = ROOT / "cases"
FIXTURE = ROOT / "fixtures" / "jd_criteria.md"
RESULTS_DIR = ROOT / "results"
REAL_WORKSPACE = pathlib.Path.home() / ".claude" / "jd-triage" / "jd_criteria.md"

# Longest-first matters: "Apply now" must win over "Apply" at the same position.
# "Confirm before applying" is the wording the spec gives CONDITIONAL its action
# line, and models emit it in place of the tier name — treat it as the tier.
ACTION_PATTERNS = [
    ("CONDITIONAL", r"CONDITIONAL|Confirm before applying"),
    ("Apply now", r"Apply\s+now"),
    ("Stretch apply", r"Stretch\s+apply"),
    ("OUT", r"OUT"),
    ("Backup", r"Backup"),
    ("Skip", r"Skip"),
    ("Apply", r"Apply"),
]


# ── case files ────────────────────────────────────────────────────────────────

def parse_case(path):
    """Front matter between --- fences, then the JD body."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{path.name}: missing front matter")
    _, fm, body = text.split("---", 2)

    meta, key = {}, None
    for line in fm.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"\s*-\s+(.*)$", line)
        if item and key:
            meta[key].append(item.group(1).strip().strip('"').strip("'"))
            continue
        kv = re.match(r"(\w+):\s*(.*)$", line)
        if kv:
            key, value = kv.group(1), kv.group(2).strip()
            if value:
                meta[key] = value.strip('"').strip("'")
                key = None
            else:
                meta[key] = []
    meta["body"] = body.strip()
    meta.setdefault("id", path.stem)
    return meta


def load_cases(only):
    cases = [parse_case(p) for p in sorted(CASES_DIR.glob("*.md"))]
    if only:
        wanted = set(only)
        cases = [c for c in cases if c["id"] in wanted or c["id"].split("-")[0] in wanted]
        missing = wanted - {c["id"] for c in cases} - {c["id"].split("-")[0] for c in cases}
        if missing:
            sys.exit(f"no such case: {', '.join(sorted(missing))}")
    if not cases:
        sys.exit("no cases found")
    return cases


# ── sandbox ───────────────────────────────────────────────────────────────────

def make_sandbox(tmp, name):
    """A self-contained copy of the skill plus a fresh workspace."""
    sandbox = tmp / name
    workspace = sandbox / "workspace"
    skill = sandbox / ".claude" / "skills" / "jd-triage"
    # exist_ok: a resumed run re-enters sandboxes left half-built by the batch
    # that was killed. Re-rendering the skill into them is idempotent.
    workspace.mkdir(parents=True, exist_ok=True)
    skill.mkdir(parents=True, exist_ok=True)

    for src_file in SRC.rglob("*"):
        if not src_file.is_file():
            continue
        dest = skill / src_file.relative_to(SRC)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            src_file.read_text(encoding="utf-8").replace("{{WORKSPACE}}", str(workspace)),
            encoding="utf-8",
        )

    today = datetime.date.today().isoformat()
    (workspace / "jd_criteria.md").write_text(
        FIXTURE.read_text(encoding="utf-8").replace("{{TODAY}}", today), encoding="utf-8"
    )
    return sandbox, workspace


# ── running ───────────────────────────────────────────────────────────────────

CONFIG = {"permission_mode": "bypassPermissions", "claude_cmd": "claude"}


def environment_note():
    """What the child process will actually talk to. Never prints the token."""
    binary = shutil.which(CONFIG["claude_cmd"]) or CONFIG["claude_cmd"]
    base = os.environ.get("ANTHROPIC_BASE_URL", "(default Anthropic API)")
    host = base.split("//")[-1].split("/")[0] if "//" in base else base
    token = "set" if os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY") else "NOT SET"
    return {
        "binary": binary,
        "endpoint": host,
        "auth": token,
        "model_env": os.environ.get("ANTHROPIC_MODEL", "(from settings)"),
    }


def build_cmd(prompt, model):
    cmd = [
        CONFIG["claude_cmd"], "-p", prompt,
        "--permission-mode", CONFIG["permission_mode"],
        "--disallowedTools", "Bash",
        "--no-session-persistence",
    ]
    if model:
        cmd += ["--model", model]
    return cmd


def invoke(sandbox, prompt, model, timeout):
    cmd = build_cmd(prompt, model)
    try:
        done = subprocess.run(
            cmd, cwd=sandbox, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return None, "timeout"
    if done.returncode != 0:
        # Claude Code reports plenty of failures on stdout, so show both streams.
        detail = " | ".join(
            part for part in ((done.stderr or "").strip(), (done.stdout or "").strip()) if part
        )
        return None, (detail[:600] or f"exit {done.returncode} with no output")
    return done.stdout, None


PROMPT_PREFIX = "Evaluate this job posting:\n\n"


def build_prompt(sandbox, body):
    """Name the skill explicitly rather than relying on auto-discovery.

    A bare "evaluate this posting" depends on the runtime finding and triggering
    the skill, and a user-level install of the same name can shadow the sandbox
    copy — which silently tests the wrong version. Pointing at the file makes the
    subject of the test unambiguous and identical across every runner.
    """
    return f"""Perform one job-posting evaluation exactly as the skill specification below defines it.

1. Read {sandbox}/.claude/skills/jd-triage/SKILL.md in full and follow it exactly.
   Load the reference files under {sandbox}/.claude/skills/jd-triage/references/ when their flow runs.
2. The criteria profile is {sandbox}/workspace/jd_criteria.md — complete and current.
   Do NOT re-bootstrap it and do NOT modify it.
3. Produce the user-facing output the skill specifies, and write it VERBATIM to
   {sandbox}/output.txt — no commentary about your process.
4. Carry out the skill's logging step as well, writing to the path the skill names.

There is no interactive user: never stop to ask. If the skill tells you to ask
something, put it where the skill says it belongs and continue.

{PROMPT_PREFIX}{body}"""


def emit(cases, runs, outdir):
    """Materialize one sandbox per run and write the prompt into it.

    Invocation is deliberately not our problem here: anything that can read
    prompt.txt, follow the skill in .claude/skills/jd-triage, and write its
    answer to output.txt can be the thing under test — the bundled CLI runner, a
    subagent, or a person pasting into a chat window. Scoring is identical.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case in cases:
        for i in range(1, runs + 1):
            name = f"{case['id']}-{i}"
            sandbox, _ = make_sandbox(outdir, name)
            (sandbox / "prompt.txt").write_text(PROMPT_PREFIX + case["body"], encoding="utf-8")
            manifest.append({"case": case["id"], "run": i, "dir": str(sandbox)})
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"{len(manifest)} sandboxes under {outdir}")
    print("each holds: prompt.txt, .claude/skills/jd-triage/, workspace/jd_criteria.md")
    print("write each answer to <sandbox>/output.txt, then: run.py --score " + str(outdir))
    return 0


def score(cases, outdir, runs):
    """Grade whatever landed in the sandboxes. No API calls."""
    manifest_file = outdir / "manifest.json"
    if manifest_file.exists():
        manifest = json.loads(manifest_file.read_text())
    else:
        # No manifest: recover the batch from the directory names alone, so a run
        # that was interrupted partway through is still fully scoreable.
        manifest = []
        for d in sorted(p for p in outdir.iterdir() if p.is_dir()):
            case_id, _, run = d.name.rpartition("-")
            if case_id and run.isdigit():
                manifest.append({"case": case_id, "run": int(run), "dir": str(d)})

    known = {c["id"]: c for c in cases}
    results = []
    for entry in manifest:
        case = known.get(entry["case"])
        if case is None:
            continue
        sandbox = pathlib.Path(entry["dir"])
        out_file = sandbox / "output.txt"
        if not out_file.exists() or not out_file.read_text(encoding="utf-8").strip():
            results.append({"case": entry["case"], "run": entry["run"], "error": "no output.txt"})
            continue
        output = out_file.read_text(encoding="utf-8")
        broken = unusable(output)
        if broken:
            results.append({"case": entry["case"], "run": entry["run"], "error": broken})
            continue
        failures, action = check_rules(case, output)
        logged = (sandbox / "workspace" / "jd_history.md").exists()
        if not logged:
            failures.append("no jd_history.md entry written")
        results.append({
            "case": entry["case"], "run": entry["run"], "action": action,
            "failures": failures, "logged": logged, "output": output,
        })
    present = [c for c in cases if any(r["case"] == c["id"] for r in results)]
    return 0 if summarize(present, results, runs) else 1


def preflight(model, timeout=90):
    """One cheap call, so a broken environment fails in a minute rather than an hour.

    `claude -p` needs its own credentials. Inside some managed or nested sessions
    it inherits ANTHROPIC_BASE_URL without a usable token and hangs instead of
    erroring — run this harness from a normal terminal.
    """
    with tempfile.TemporaryDirectory(prefix="jd-triage-preflight-") as d:
        out, err = invoke(pathlib.Path(d), "Reply with exactly: PONG", model, timeout)
    if out is None:
        env = environment_note()
        shown = " ".join(
            f"'{a}'" if " " in a else a for a in build_cmd("Reply with exactly: PONG", model)
        )
        sys.exit(
            f"preflight failed: {err}\n\n"
            f"  binary:   {env['binary']}\n"
            f"  endpoint: {env['endpoint']}\n"
            f"  auth:     {env['auth']}\n"
            f"  command:  {shown}\n\n"
            "  If auth is NOT SET and your shell reaches Claude through an alias or\n"
            "  wrapper, this harness never sees it — subprocess execs the binary\n"
            "  directly and aliases do not apply. Export the variables your alias\n"
            "  sets (ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN) before running.\n\n"
            "  If auth is set and the call still fails, run the command above by hand\n"
            "  to see the real error; --permission-mode takes another value if that\n"
            "  flag is what is being rejected."
        )
    if not out.strip():
        sys.exit("preflight returned an empty response — the call completed but produced nothing.")
    if "PONG" not in out.upper():
        # Connectivity is what preflight exists to check; echoing the token is not.
        # Worth one line though: a model that will not repeat "PONG" on request is
        # a model whose rule-following the suite is about to measure.
        print(f"(note: preflight replied {out.strip()[:40]!r} rather than PONG)", end=" ")


def dry_run():
    """Materialize one sandbox and check it without spending a single API call."""
    with tempfile.TemporaryDirectory(prefix="jd-triage-dry-") as d:
        sandbox, workspace = make_sandbox(pathlib.Path(d), "dry")
        skill = sandbox / ".claude" / "skills" / "jd-triage"
        files = sorted(p.relative_to(skill).as_posix() for p in skill.rglob("*") if p.is_file())
        text = "\n".join((skill / f).read_text(encoding="utf-8") for f in files)

        problems = []
        if "{{" in text:
            problems.append("unsubstituted {{TOKEN}} left in the rendered skill")
        if str(workspace) not in text:
            problems.append("workspace path was not substituted into the skill")
        if not (workspace / "jd_criteria.md").exists():
            problems.append("fixture criteria not placed in the workspace")
        if "{{TODAY}}" in (workspace / "jd_criteria.md").read_text(encoding="utf-8"):
            problems.append("{{TODAY}} not substituted in the fixture")

        print(f"skill files rendered: {len(files)}")
        for f in files:
            print(f"  {f}")
        print(f"workspace: {workspace}")
        print(f"criteria:  {(workspace / 'jd_criteria.md').stat().st_size} bytes")
        if problems:
            for p in problems:
                print(f"FAIL: {p}")
            return 1
        print("\nsandbox ok — every token substituted, fixture in place")
        return 0


def action_in(text):
    """Longest match wins at the earliest position, case-insensitively."""
    best = None
    for name, pattern in ACTION_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if not m:
            continue
        if best is None or m.start() < best[1] or (m.start() == best[1] and len(name) > len(best[0])):
            best = (name, m.start())
    return best[0] if best else None


def extract_action(output):
    """Read the verdict line only.

    Scanning the whole document was wrong: prose like "this does not trigger an
    OUT" outranked the real headline, and casing varied ("Apply now" vs
    "APPLY NOW"). The template guarantees a headline that either carries the
    Desirability/Candidacy pair or, for a hard gate, opens the output.
    """
    lines = output.splitlines()

    for line in lines:
        if "Desirability" in line:
            head = line.split("Desirability")[0]
            found = action_in(head) or action_in(line)
            if found:
                return found

    # Hard-gate and refusal outputs have no Desirability pair; take the first
    # line that opens with an action, ignoring any leading emoji or bullet.
    for line in lines[:12]:
        stripped = re.sub(r"^[^\w]*", "", line).strip()
        if not stripped:
            continue
        found = action_in(stripped[:60])
        if found and stripped[:60].lower().startswith(
            tuple(f.lower()[:4] for f in ("OUT", "CONDITIONAL", "Confirm", "Apply", "Stretch", "Backup", "Skip"))
        ):
            return found
    return None


def unusable(text):
    """Why this text is not an evaluation, or None if it looks like one.

    A CLI that fails mid-flight can still exit 0 having printed something short
    like "Execution error". Scored naively that reads as a skill that broke every
    rule at once, which quietly turns an infrastructure problem into a quality
    number. Infrastructure failures belong in the error column.
    """
    stripped = (text or "").strip()
    if not stripped:
        return "empty output"
    if len(stripped) < 80 or extract_action(stripped) is None:
        return f"unusable output ({len(stripped)} bytes): {stripped[:60]!r}"
    return None


def check_rules(meta, output):
    """Layer 2. Returns a list of failure strings; empty means compliant."""
    failures = []
    action = extract_action(output)

    expected = meta.get("expect_action")
    if expected and action != expected:
        failures.append(f"action={action or 'none'}, expected {expected}")

    forbidden = meta.get("expect_action_not") or []
    if action in forbidden:
        failures.append(f"action={action} is forbidden here")

    for pattern in meta.get("must_match") or []:
        if not re.search(pattern, output, re.IGNORECASE | re.MULTILINE):
            failures.append(f"missing /{pattern}/")

    for pattern in meta.get("must_not_match") or []:
        if re.search(pattern, output, re.IGNORECASE | re.MULTILINE):
            failures.append(f"unexpected /{pattern}/")

    return failures, action


def run_once(tmp, case, index, model, timeout):
    name = f"{case['id']}-{index}"
    sandbox, workspace = make_sandbox(tmp, name)
    output, error = invoke(sandbox, build_prompt(sandbox, case["body"]), model, timeout)
    if output is None:
        return {"case": case["id"], "run": index, "error": error}

    # The run writes output.txt itself; keep stdout only as a fallback so that
    # every run leaves an inspectable artifact on disk either way.
    written = sandbox / "output.txt"
    if written.exists() and written.read_text(encoding="utf-8").strip():
        output = written.read_text(encoding="utf-8")
    else:
        written.write_text(output, encoding="utf-8")

    broken = unusable(output)
    if broken:
        # Leave the file on disk to be read, but do not score it as an answer.
        return {"case": case["id"], "run": index, "error": broken}

    failures, action = check_rules(case, output)
    logged = (workspace / "jd_history.md").exists()
    if not logged:
        failures.append("no jd_history.md entry written")

    return {
        "case": case["id"],
        "run": index,
        "action": action,
        "failures": failures,
        "logged": logged,
        "output": output,
    }


# ── reporting ─────────────────────────────────────────────────────────────────

def summarize(cases, results, runs):
    by_case = {c["id"]: [] for c in cases}
    for r in results:
        by_case[r["case"]].append(r)

    print(f"\n{'case':<26} {'actions':<34} {'stable':<7} rules")
    print("─" * 92)

    consistent = checked = 0
    rule_pass = rule_total = 0
    modal = {}

    for case in cases:
        rs = by_case[case["id"]]
        errors = [r for r in rs if "error" in r]
        good = [r for r in rs if "error" not in r]
        actions = [r["action"] or "?" for r in good]
        modal[case["id"]] = actions[0] if actions and len(set(actions)) == 1 else None

        if good:
            checked += 1
            stable = len(set(actions)) == 1
            consistent += stable
            mark = "yes" if stable else "NO"
        else:
            mark = "—"

        failures = sorted({f for r in good for f in r["failures"]})
        rule_total += len(good)
        rule_pass += sum(1 for r in good if not r["failures"])

        shown = ", ".join(dict.fromkeys(actions)) or "—"
        note = "; ".join(failures) if failures else "ok"
        if errors:
            note = f"{len(errors)} run(s) failed: {errors[0]['error']}" + (
                f" | {note}" if failures else ""
            )
        print(f"{case['id']:<26} {shown[:33]:<34} {mark:<7} {note}")

    # Paired-case rules: two cases that must land differently, or identically.
    print()
    pairs = {}
    for case in cases:
        if case.get("pair") and case.get("pair_expect"):
            pairs.setdefault(case["pair"], []).append(case)

    pair_pass = pair_total = 0
    for pair, members in sorted(pairs.items()):
        if len(members) != 2:
            continue
        a, b = (modal[m["id"]] for m in members)
        rule = members[0]["pair_expect"]
        if a is None or b is None:
            verdict = "unstable — cannot judge"
        else:
            ok = (a != b) if rule == "differ" else (a == b)
            pair_total += 1
            pair_pass += ok
            verdict = "ok" if ok else f"FAIL — both/neither ({a} vs {b})"
        print(f"pair {pair:<28} must {rule:<7} {members[0]['id']}={a} {members[1]['id']}={b}  {verdict}")

    print("\n" + "─" * 92)
    pct = lambda n, d: f"{100 * n / d:.0f}%" if d else "n/a"
    if runs < 2:
        # A single sample is trivially "stable"; printing 100% here would be a lie.
        print("consistency      not measured — needs --runs 2 or more")
    else:
        print(f"consistency      {consistent}/{checked} cases stable across {runs} runs   {pct(consistent, checked)}")
    print(f"rule compliance  {rule_pass}/{rule_total} runs clean                  {pct(rule_pass, rule_total)}")
    print(f"paired contrast  {pair_pass}/{pair_total} pairs separated correctly   {pct(pair_pass, pair_total)}")
    return consistent == checked and rule_pass == rule_total and pair_pass == pair_total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--model", default=None)
    # An agentic run reads SKILL.md plus several references before answering.
    # Measured 65-350s on Sonnet; slower models need more headroom than that.
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--keep-output", action="store_true", help="store full text of every run")
    ap.add_argument("--dry-run", action="store_true", help="build a sandbox and check it, no API calls")
    ap.add_argument("--skip-preflight", action="store_true")
    ap.add_argument(
        "--permission-mode",
        default=CONFIG["permission_mode"],
        help="passed to claude -p; use another mode if bypassPermissions is rejected",
    )
    ap.add_argument(
        "--claude-cmd",
        default=CONFIG["claude_cmd"],
        help="path to the claude binary, if it is not plain `claude` on PATH",
    )
    ap.add_argument("--emit", metavar="DIR", help="build sandboxes + prompts, run nothing")
    ap.add_argument("--score", metavar="DIR", help="grade output.txt files from a previous --emit")
    ap.add_argument("--resume", metavar="DIR", help="finish an interrupted run, skipping cases already answered")
    args = ap.parse_args()
    CONFIG["permission_mode"] = args.permission_mode
    CONFIG["claude_cmd"] = args.claude_cmd

    if args.dry_run:
        return dry_run()

    if args.emit:
        return emit(load_cases(args.only), args.runs, pathlib.Path(args.emit))

    if args.score:
        return score(load_cases(args.only), pathlib.Path(args.score), args.runs)

    if not shutil.which(args.claude_cmd) and not os.path.exists(args.claude_cmd):
        sys.exit(f"claude CLI not found: {args.claude_cmd}")

    env = environment_note()
    print(f"binary {env['binary']} · endpoint {env['endpoint']} · auth {env['auth']} · model {env['model_env']}")

    cases = load_cases(args.only)
    if not args.skip_preflight:
        print("preflight…", end=" ", flush=True)
        preflight(args.model)
        print("ok")

    before = REAL_WORKSPACE.stat().st_mtime if REAL_WORKSPACE.exists() else None

    print(f"{len(cases)} cases × {args.runs} runs = {len(cases) * args.runs} invocations, {args.jobs} at a time")

    results = []
    # Sandboxes persist: an aborted or surprising run must still leave every
    # output on disk. Discarding them costs a full re-run of real API calls.
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    RESULTS_DIR.mkdir(exist_ok=True)
    if args.resume:
        # resolve(): a relative --resume path otherwise breaks display paths later.
        tmp = pathlib.Path(args.resume).resolve()
        if not tmp.is_dir():
            sys.exit(f"no such run directory: {tmp}")
    else:
        tmp = RESULTS_DIR / f"run-{stamp}"
        tmp.mkdir()
    print(f"sandboxes: {tmp}")

    jobs = [(c, i) for c in cases for i in range(1, args.runs + 1)]
    if args.resume:
        # Skip whatever already answered. A batch killed partway through should
        # cost only the remainder, not the whole suite again.
        before_count = len(jobs)

        def needs_rerun(case, index):
            f = tmp / f"{case['id']}-{index}" / "output.txt"
            if not f.exists():
                return True
            # Same usability test as scoring, so a run that died mid-flight and
            # left "Execution error" behind is retried rather than counted as done.
            return unusable(f.read_text(encoding="utf-8")) is not None

        jobs = [(c, i) for c, i in jobs if needs_rerun(c, i)]
        print(f"resuming: {before_count - len(jobs)} already done, {len(jobs)} to go")
        if not jobs:
            return score(cases, tmp, args.runs)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {
            pool.submit(run_once, tmp, c, i, args.model, args.timeout): (c, i)
            for c, i in jobs
        }
        for n, fut in enumerate(concurrent.futures.as_completed(futures), 1):
            r = fut.result()
            results.append(r)
            # Surface failures the moment they happen. A silent counter climbing
            # to 36/36 hides the fact that every one of them errored.
            if "error" in r:
                print(f"\r  {n}/{len(jobs)}  ✗ {r['case']} run {r['run']}: {r['error'][:120]}")
            else:
                print(f"\r  {n}/{len(jobs)} done", end="", flush=True)
    print()

    # A warning, never an abort — the numbers below still mean something, and
    # the raw outputs are on disk to be read either way.
    usable = [r for r in results if "error" not in r]
    if usable and not any("Candidacy" in r["output"] for r in usable):
        print(
            "\nWARNING: no output contains a Candidacy section. Either the runs did not\n"
            "         follow src/SKILL.md, or an older jd-triage shadowed the sandbox copy.\n"
            f"         Read {tmp}/<case>-<run>/output.txt before trusting anything below.\n"
        )

    after = REAL_WORKSPACE.stat().st_mtime if REAL_WORKSPACE.exists() else None
    if before != after:
        print("\nWARNING: the real ~/.claude/jd-triage/jd_criteria.md changed during this run.")

    # Persist before summarizing: a crash in the report must not cost the run.
    payload = [
        {k: v for k, v in r.items() if k != "output" or args.keep_output} for r in results
    ]
    out = RESULTS_DIR / f"{stamp}.json"
    out.write_text(
        json.dumps(
            {
                "runs": args.runs,
                "model": args.model,
                # Which model answered matters for reading these numbers later.
                "environment": {k: v for k, v in environment_note().items() if k != "auth"},
                "results": payload,
            },
            indent=2,
        )
    )
    def shown(p):
        try:
            return p.relative_to(REPO)
        except ValueError:      # a path outside the repo is still worth printing
            return p

    print(f"\nresults  {shown(out)}")
    print(f"outputs  {shown(tmp)}/<case>-<run>/output.txt")

    # Score the whole directory, not just this invocation's slice. A resumed run
    # only executes what was missing, and summarizing those alone reports every
    # previously-finished case as absent.
    return score(cases, tmp, args.runs)


if __name__ == "__main__":
    sys.exit(main())
