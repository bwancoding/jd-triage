# evals

Two things are measured here, and neither needs anyone to label a "correct"
verdict:

**Layer 1 — consistency.** Run the same posting N times. Do you get the same
action every time? This needs no ground truth at all. Where the spec is
ambiguous, the model resolves it differently on different runs, so instability
is a *location*: the cases that wobble point at the rules still worth tightening.

**Layer 2 — rule compliance.** Did the skill follow its own stated rules? Did the
vibe line actually quote the posting? Did a missing salary become
`(info insufficient)` rather than a quiet 3★? Did the history entry get written?
These are the selling points, and a selling point that does not fire is a feature
that does not exist. All of it is checkable with regexes.

Not measured here: whether the advice is any good. That needs real outcomes —
the `Outcome` field in `jd_history.md`, months from now.

## Running it

```bash
./evals/run.py                       # 18 cases × 3 runs
./evals/run.py --only 01a 07a        # a subset, by id or prefix
./evals/run.py --runs 5 --jobs 6
./evals/run.py --model sonnet
./evals/run.py --dry-run             # build a sandbox and check it, no API calls
```

Needs a logged-in `claude` CLI on PATH. A preflight sends one trivial prompt
first, so a broken environment fails in a minute instead of an hour.

**Run it from a normal terminal.** Inside a nested or managed Claude Code
session, the child `claude` process inherits `ANTHROPIC_BASE_URL` without a
usable credential and hangs rather than failing; the preflight will tell you so.

Every run gets a throwaway sandbox holding its own rendered copy of `src/` and
its own workspace, so runs cannot interfere with each other and none of them can
reach your real `~/.claude/jd-triage/`. The harness checks that file's mtime
before and after and warns if it moved.

## What the output means

```
consistency      16/18 cases stable across 3 runs   89%
rule compliance  52/54 runs clean                   96%
paired contrast   8/9 pairs separated correctly     89%
```

The third line is the one to read first. Nine cases are written as **pairs** that
differ in exactly one respect, so a pair that fails to separate is a specific
broken rule, not a vague quality problem.

| Pair | The one thing that differs | What a failure means |
|---|---|---|
| `redline-position` | A red line in the title vs. the same phrase in a tail bullet framed as *support* | Responsibility weighting is not firing — the headline feature |
| `redline-semantics` | "partner with Revenue Operations" vs. "carry an individual quota" | Red-line matching is either string-matching or hallucinating |
| `anchor-reasoning` | A famous anchor (Basecamp) vs. a fictional one (Stroom Werkplaats) | If only the famous one is cited, vibe reasons from reputation instead of the user's `why` — generalization is broken |
| `intensity-language` | The same posting in German and in English | The per-language intensity table is not being consulted |
| `comp-basis` | "€95,000 base + bonus" vs. "€95,000 total package" | Comp is being compared across different bases |
| `requirement-count` | 2 stated must-haves vs. 6 | The Candidacy `Unknown` → provisional path is missing |
| `two-dimensions` | Want-it-can't-get vs. can-get-don't-want | The two dimensions have collapsed back into one score |
| `posting-density` | A three-line posting vs. a complete one | The skill scores things it should refuse to score |

Two fictional anchors sit in `fixtures/jd_criteria.md` on purpose. No model can
have prior knowledge of *Stroom Werkplaats* or *Kettle Group*, so any reasoning
about them has to come from the `why` field — which is exactly the property that
lets the skill work for someone whose favourite employer is a nine-person studio
nobody has written about.

## Adding a case

Drop a markdown file in `cases/`. Front matter, then the posting:

```markdown
---
id: 10a-something
pair: some-contrast          # optional
pair_expect: differ          # differ | same
expect_action: OUT           # optional
expect_action_not:
  - Skip
must_match:
  - "regex, case-insensitive"
must_not_match:
  - "regex"
---

**Job title** — City
...
```

Prefer pairs over singletons. A case that only asserts "this should be OUT" is
weak evidence — the model can get it right for the wrong reason. A pair that must
separate isolates the actual rule.

Keep the fixture profile fixed. If you change `fixtures/jd_criteria.md`, previous
results stop being comparable — that is the eval equivalent of moving the goalposts.
