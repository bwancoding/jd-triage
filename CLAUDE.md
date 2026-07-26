# Working in this repo

Read this before touching anything. It is short on purpose.

## The one thing that trips everyone

`src/` is the only place to edit. `claude-code/` and `openclaw/` are **generated**
by `build.sh` and committed so they can be installed directly.

Editing a generated directory looks exactly like editing a normal file, right up
until the next `./build.sh` silently overwrites it. If a change belongs in the
skill, it belongs in `src/`.

```
src/                    edit here
  SKILL.md              main behaviour
  references/*.md       loaded per flow
  assets/               criteria template + presets
platform/openclaw/      hub listing page + publishing metadata
claude-code/            GENERATED — do not edit
openclaw/               GENERATED — do not edit
```

`{{WORKSPACE}}` in `src/` is substituted per platform (`~/.claude/jd-triage` or
`~/.openclaw/workspace`). Leave the token alone in `src/`.

## Before you call anything done

Every one of these must pass. CI runs the same set, so a red result here is a red
result on the pull request.

```bash
./build.sh              # regenerate after any src/ change
./build.sh --check      # generated dirs match src/
python3 evals/run.py --dry-run
python3 -m json.tool platform/openclaw/_meta.json
```

Forgetting `./build.sh` after editing `src/` is the most common failure: the
change is real but the installable copies still hold the old text, and `--check`
will say so.

## Known traps

- **`.gitignore` carries a bare `jd_criteria.md`** so nobody commits their real
  criteria. That pattern matches the name at any depth. `evals/fixtures/jd_criteria.md`
  is negated back in explicitly — if you add another fixture with a protected
  name, it will vanish from the repo without a word.
- **`evals/results/` is ignored**; sandboxes and run output live there and are
  never committed. `evals/baselines/` *is* committed.
- **Do not edit `evals/fixtures/jd_criteria.md`.** Every recorded baseline was
  scored against it; changing it silently invalidates all of them.
- **Do not edit files under `evals/baselines/`.** A hand-tidied baseline is
  worthless for diffing.
- Two fixture vibe anchors (*Stroom Werkplaats*, *Kettle Group*) are fictional on
  purpose. They test that the skill reasons from each anchor's stated `why`
  rather than from an organization's reputation. Do not "correct" them to real
  companies.

## Running the eval suite

Costs real API calls, so it is never run in CI and never run casually.

```bash
./evals/run.py --only 01a 07a --runs 1   # smoke test first, 2 calls
./evals/run.py --runs 2                  # full suite, 36 calls
./evals/run.py --resume <dir>            # finish an interrupted run
./evals/run.py --score <dir>             # re-grade on disk, no calls
```

Sandboxes persist under `evals/results/run-<timestamp>/`. Nothing is ever
discarded on failure — if a number looks wrong, read `<case>/output.txt` before
theorising.

## Picking up work

Queued tasks live in `.claude/tasks/`, lowest number first; finished ones move to
`.claude/tasks/done/` and stay there as a build log. Run `/next` to take the
oldest one — it reads the task, applies this file's constraints, runs the task's
own acceptance commands, and files it away when they pass.

Each task states its own boundary and acceptance. Those are the contract: work
outside the boundary, or a green report with a red command in it, is a failed
task even if the code is good.

## Where judgement is required, stop

These are not for a coding pass to decide alone. Raise them instead:

- Changing a scoring rule, an axis weight, or a verdict tier boundary
- Changing what a test case asserts (as opposed to fixing a broken harness)
- Anything that would make a published number in `README.md` no longer true
- Anything touching the criteria schema — existing users' files migrate against it

A test that passes is not the same as a rule that is right. Six specification
defects in this repo were found by reading output that every mechanical
assertion had already approved.
