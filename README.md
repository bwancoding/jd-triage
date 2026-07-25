# jd-triage

**v1.1.0** · A career-criteria-aware job-posting triage skill, for Claude Code and OpenClaw.

Paste a job posting. The skill scores it on **two independent dimensions** —
*do you want it* and *can you get it* — and returns one action.

> **Design ethos**: most JD filters are keyword matchers that emit a single
> score. Real screening is judgment under uncertainty about two different
> questions, and collapsing them destroys the answer. This skill keeps them
> apart, and makes each one inspectable: every vibe rating quotes the posting and
> names the anchor it reasoned from, every red-line hit is located in the posting
> with its surrounding framing, and every unknown becomes a question you can send
> to a recruiter instead of a silent assumption.

---

## Why two dimensions

| | Likely | Plausible | Stretch |
|---|---|---|---|
| **Strong** | 🔥 Apply now | 🔥 Apply now | 🎯 Stretch apply |
| **Good** | ✅ Apply | ✅ Apply | 🎯 Stretch apply |
| **Weak** | 🗄️ Backup | 🗄️ Backup | ❌ Skip |
| **Poor** | ❌ Skip | ❌ Skip | ❌ Skip |

A single ordinal verdict cannot distinguish *"you'd love this and you're a long
shot"* from *"you'd tolerate this and you'd walk in"* — but those two demand
completely different behaviour from you. **Desirability** is a weighted average
of five axes scored against your stored criteria. **Candidacy** is the hit rate
of the posting's stated must-have requirements against your skills inventory,
with half credit for anything you are actively learning.

Hard gates and red lines short-circuit before either is computed.

## What it does differently

### Red lines are weighted by position, not matched as strings

"Owns the revenue target" in the **title** is an instant no. The same idea in the
**last bullet, framed as *support***, surrounded by six bullets of work you want,
is a question for the recruiter — not a rejection.

| Where the matched responsibility sits | Verdict |
|---|---|
| Title, first 1–2 bullets, or plausibly >30% of the role | ❌ **OUT** |
| Tail bullets, framed as support / assist / partner-with | ⚠️ **CONDITIONAL** + open questions |
| Requirements section only, not the duties | Noted, does not gate |

Matching is **semantic**, so a red line written in one language catches a posting
written in another — and so `"growth"` does not fire on `"growth mindset"` in a
values paragraph.

### Vibe anchors carry your reason, not just a name

`vibe_anchors_positive: ["Linear"]` only works if the model already has an
opinion about Linear. That fails silently for a 12-person studio in your city, and
fails *invisibly* for famous companies, where the model substitutes reputation for
your actual taste.

So every anchor requires a `why`:

```yaml
- name: "Linear"
  why: "restraint — a clear product opinion, no feature-count race"
```

The `why` is the comparison basis. Obscure anchors now work exactly as well as
famous ones, and the rating stays yours.

### Rejections still produce signal

An `OUT` verdict outputs a **Matched anyway** block naming what did align, and
still writes a history entry. `/jd-triage analyze` reads those rows later to tell
you which pattern keeps reaching your inbox and which requirement you keep
almost meeting.

### Unknowns become questions

Missing comp, ambiguous scope, unstated remote policy: each becomes a line under
**Open questions**, phrased so you can paste it into a reply. No silent
`unknown → assume fine`.

### Five questions to start

Quick Start asks for your role family and market, your target titles and domains,
your floors, your automatic no's, and one to three anchors with reasons. Skills,
org traits, and negative anchors are captured **just in time** — once, at the
moment the first evaluation actually needs them.

`/jd-triage learn` skips the interview entirely: hand it a few postings you liked
and a few you passed on, and it proposes your red lines and anchors, each with the
evidence it came from, for you to accept or edit.

---

## Generality

Market-, language-, and profession-neutral by construction:

- **No fixed company taxonomy.** `org_traits` is a free list of traits in your own
  words with your own weights — `"research lab with a shipping product": 5` and
  `"private-equity owned": 1` use the same machinery.
- **Comp is structured**, with `basis` (`base` / `total` / hourly), currency,
  period, and conventions like 13th-month or base-plus-equity. The skill compares
  like for like and refuses to invent an exchange rate.
- **Intensity signals are per-language data**, not hardcoded keywords —
  see [`src/references/intensity-signals.md`](src/references/intensity-signals.md).
- **Seniority is never mapped across markets.** L5, P7, and Grade 6 are not
  comparable; the skill counts stated requirements and ignores the label.
- **English-first output**, switching to whatever language you write in. Stored
  keys stay English so the files stay greppable; stored values keep the language
  you wrote them in and are never retroactively translated.

---

## Install

**Claude Code**

```bash
cp -r claude-code ~/.claude/skills/jd-triage
```

**OpenClaw** — published on [ClawHub](https://clawhub.ai/bwancoding/jd-triage):

```bash
openclaw skills install @bwancoding/jd-triage
```

Or through the `skills` runner:

```bash
npx skills add https://clawhub.ai/bwancoding/skills/jd-triage
```

Or straight from this repo — copy `openclaw/`, the built directory whose paths
are already resolved. Do **not** copy `src/`; its paths are still `{{WORKSPACE}}`
placeholders and will point nowhere.

```bash
cp -r openclaw ~/.openclaw/plugin-skills/jd-triage
```

Then `/skill enable jd-triage`.

Upgrading from an earlier version? Leave your `jd_criteria.md` alone — the skill
detects `schema_version < 3` and migrates on next run, asking only for what it
cannot infer (comp basis, one `why` per red line and anchor, and your market
context). Ratings of `3` in the old company-type and company-size maps are
dropped, because they never changed an outcome.

---

## Repo layout

`src/` is the only place to edit. The two platform directories are **generated**
and committed so they can be installed directly.

```
jd-triage/
├── src/                            ← single source of truth
│   ├── SKILL.md
│   ├── assets/
│   │   ├── criteria-template.yaml  schema v3
│   │   └── presets/                menus offered at Quick Start, never defaults
│   └── references/
│       ├── bootstrap.md            quick start · learn-from-examples · full · migration
│       ├── scoring.md              5 axes + candidacy, with worked examples
│       ├── intensity-signals.md    per-language intensity vocabulary
│       ├── history.md              log format, history, compare
│       └── analysis-commands.md    analyze, plan
├── platform/openclaw/              hub listing page + publishing metadata
├── build.sh                        src/ → claude-code/ + openclaw/
├── claude-code/                    generated
└── openclaw/                       generated
```

```bash
./build.sh          # regenerate both platform directories
./build.sh --check  # fail if they are out of sync with src/
```

`{{WORKSPACE}}` in `src/` is substituted per platform
(`~/.claude/jd-triage` / `~/.openclaw/workspace`). Run `./build.sh` before
committing; `--check` is safe to wire into CI or a pre-commit hook.

---

## Status

**v1.1.0** — two-dimension verdict with a Candidacy axis; generalized to any
market, language, and profession; 5-question Quick Start with just-in-time
capture; derive-criteria-from-examples; per-language intensity signals; structured
comp with basis comparison; single-source build.

Verdict precedence is now explicit and single-valued (gate → conditional →
matrix), replacing the overlapping tier rules of earlier versions.

Verified on GLM-5.2 and Claude Sonnet 4.6. Smaller models are untested — see
[Evals](#evals) for what has and has not been measured.

### Evals

[`evals/`](evals/) measures two things that need no human labelling: whether the
same posting produces the same action across repeated runs, and whether the skill
followed its own stated rules (vibe citations present, missing comp marked
insufficient rather than padded, history entry written).

```bash
./evals/run.py            # 18 cases × 3 runs
./evals/run.py --dry-run  # check the harness itself, no API calls
```

Nine of the cases are **pairs** differing in exactly one respect — a red line in
the title vs. the same phrase in a tail support bullet, a famous vibe anchor vs. a
fictional one, the same posting in German and English. A pair that fails to
separate names a specific broken rule instead of a vague quality problem. See
[`evals/README.md`](evals/README.md).

Measured on GLM-5.2, 18 cases × 2 runs:

```
consistency      18/18 cases stable across 2 runs   100%
rule compliance  36/36 runs rule-compliant          100%
paired contrast   6/6 pairs separated correctly     100%
```

Those numbers are the *result* of running it, not the reason to trust it. The
first pass found six specification defects — an unpinned verdict token, no
defined action for "too thin to score", literal domain matching that scored the
same domain differently in two postings, an undefined `org_fit` when traits were
assessable but absent, and `CONDITIONAL` firing on unknowns that could not change
the outcome. All are fixed; the suite exists to catch the next six.

**What these numbers do not establish:**

- **Whether the advice is good.** Consistency and rule-following are what is
  measured here. Real validation needs the `Outcome` field in your history,
  filled in over months.
- **Anything about small models.** An earlier version of this README claimed
  failures below ~30B. That number had no evidence behind it and is gone. What is
  measured: GLM-5.2 and Claude Sonnet 4.6 both follow the specification, and on
  one rule — a red line sitting in a tail support bullet — GLM-5.2 was the more
  accurate of the two.
- **The true instability rate.** Two runs detect disagreement but understate it;
  three or more would be firmer.
- **A clean cross-model comparison.** The committed Sonnet baseline was recorded
  against the *pre-fix* specification, so it documents the starting point rather
  than a like-for-like benchmark.

100% is also only 100% *against the assertions that exist*. Reading one output by
hand found two real defects that every mechanical check had passed. Mechanical
assertions catch regressions; they do not replace occasionally reading the output.

---

## License

MIT — see [`LICENSE`](./LICENSE).

## Author

Barry Wang ([@bwancoding](https://github.com/bwancoding))
