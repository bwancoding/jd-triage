# jd-triage

A career-criteria-aware Job Description triage skill that runs on two AI agent platforms.

Paste a JD; the skill checks it against your stored hiring criteria, applies hard gates with **responsibility-weighted** red lines, scores six soft axes on a 5-star rubric with **mandatory anchor-cited vibe judgments**, and returns a verdict in one of six tiers — including a `CONDITIONAL` state that surfaces concrete questions to ask the recruiter instead of false-OUT-ing borderline JDs.

> **Design ethos**: most JD-screening tools are keyword filters. Real screening is judgment under uncertainty. This skill makes the model's reasoning legible — every vibe rating cites a specific anchor and JD phrase, every red-line hit is located in the JD with its surrounding wording, and every unknown becomes an explicit `Open question` instead of a silent assumption.

---

## Two versions, one source of truth

| Version | Runtime | Install path | Criteria/history location |
|---|---|---|---|
| [`openclaw/`](./openclaw/) | OpenClaw + ClawdHub | `~/.openclaw/plugin-skills/jd-triage/` | `~/.openclaw/workspace/jd_criteria.md` |
| [`claude-code/`](./claude-code/) | Claude Code | `~/.claude/skills/jd-triage/` | `~/.claude/jd-triage/jd_criteria.md` |

Both versions share the same evaluation logic, scoring rubric, and bootstrap flow. They differ only in:

- **Storage paths** (each platform's convention)
- **Publishing metadata** (OpenClaw version has `_meta.json` and a hub-facing `README.md`)

Edits to evaluation logic should land in **both** versions.

---

## What makes this skill different

Most JD-triage prompts I've seen do roughly: *"score this JD against these keywords, return a verdict."* That produces confident-sounding nonsense. This skill enforces four hard rules that cost a few extra tokens but produce judgments you can actually act on:

### 1. Responsibility-weighted red lines

A keyword like `"商业化"` ("commercialization") in the **last bullet, framed as `支持` (support)**, surrounded by 6 bullets of Agent/RAG/Prompt work, is **not** the same as `"商业化"` in the **job title** or **first responsibility**. The skill applies a three-tier weight rule:

| Where the red-line keyword appears | Verdict |
|---|---|
| In JD title, OR first 1–2 bullets, OR estimated >30% of role | **❌ OUT** (core responsibility) |
| Only in tail bullets, framed as "支持/协助/support/assist" | **⚠️ CONDITIONAL** (proceed to soft scoring + open questions) |
| Only in qualifications / preferred skills section | Note as open question, do not gate |

This avoids the most common failure mode of keyword filters: false-OUT-ing JDs that are actually 80%+ aligned but mention a sensitive word once in passing.

### 2. Mandatory anchor citation on vibe scoring

Vibe scoring is the load-bearing axis (a 1★ vibe alone can drag the verdict down a tier). To prevent the model from making up vibes by feel, every vibe rating is required to:

- Name at least one specific anchor (positive or negative) from the user's criteria file
- Quote the exact JD phrase that triggered the comparison

Adjective-only verdicts ("looks growth-y", "no product taste") are explicitly forbidden in the rubric. This makes vibe judgments inspectable — you can see whether the model is using your anchors or making things up.

### 3. Strengths summary on OUT

Even when a JD fails a hard gate, the skill outputs a `Strengths matched` section listing axes that *did* align (e.g. *"language environment matches foreign-company preference"*, *"core responsibilities hit Agent + RAG keywords"*). Skipping shouldn't waste signal — over time these strengths accumulate into a sharper sense of "what kind of company should I watch for."

### 4. Open questions as first-class output

When salary is unknown, location is ambiguous, or a `CONDITIONAL` is in play, the skill outputs an `Open questions` block: concrete things to ask the recruiter, in the recruiter's expected register. No silent `unknown → continue` fallthrough.

---

## Verdict tiers

| Tier | Meaning |
|---|---|
| ✅ **Strong Apply** | All axes ≥ 4★, no hard-gate near-miss |
| 🎯 **Apply** | Average ≥ 3.5★, no axis below 2★, vibe ≥ 3★ |
| ⚠️ **Conditional** | Red-line keyword in non-core responsibility, OR critical unknowns; proceed with `Open questions` |
| ⚠️ **Caution** | Average ≥ 2.5★, OR vibe = 1–2★ |
| ❌ **Skip** | Average < 2.5★, OR any high-weight axis = 1★ |
| ❌ **OUT** | Hard gate failed (core-responsibility red line, salary below floor, city mismatch, lifestyle exceeds tier) |

---

## Bootstrap & lifecycle

On first run the skill walks you through three blocks of questions (Profile / Hard Gates / Soft Axes), 13 fields total, and writes them to `jd_criteria.md`. On subsequent runs:

- ≤ 15 days old → use as-is
- > 15 days old → one-line `y/n` freshness check; partial patches if anything changed
- Schema gap → asks only the missing fields
- Explicit `update` / `reset` → full re-bootstrap with current values pre-filled

Each evaluation appends to `jd_history.md` with a `JD-YYYYMMDD-NNN` ID, the verdict, scores, and the `criteria_version` in effect at evaluation time. Compare past evaluations with `/jd-triage compare <id1> <id2>`.

---

## Repo layout

```
jd-triage/
├── README.md                 ← this file (design overview)
├── LICENSE
├── .gitignore
├── openclaw/                 ← OpenClaw / ClawdHub publish target
│   ├── SKILL.md
│   ├── README.md             ← ClawdHub listing page
│   ├── _meta.json
│   ├── assets/
│   │   └── criteria-template.yaml
│   └── references/
│       ├── bootstrap-questions.md
│       ├── scoring-rubric.md
│       └── history-format.md
└── claude-code/             ← Claude Code version
    ├── SKILL.md
    ├── assets/
    │   └── criteria-template.yaml
    └── references/
        ├── bootstrap-questions.md
        ├── scoring-rubric.md
        └── history-format.md
```

---

## Install

### OpenClaw

```bash
cp -r openclaw ~/.openclaw/plugin-skills/jd-triage
```

Then in OpenClaw:

```
/skill enable jd-triage
```

Or publish to ClawdHub (requires ClawdHub account configured):

```bash
cd openclaw
openclaw publish
```

### Claude Code

```bash
cp -r claude-code ~/.claude/skills/jd-triage
```

Claude Code will auto-discover the skill on next session. Trigger it with `/jd-triage` or by pasting a JD.

---

## Status

**v0.2** — `CONDITIONAL` tier, responsibility-weighted red lines, anchor-cited vibe scoring, strengths-on-OUT, open-questions-as-output. Tested with GLM 4.5 / GLM 5.1 (SiliconFlow) on OpenClaw and with Claude Sonnet on Claude Code.

Smaller open-source models (≤14B) are **not supported** — the skill assumes frontier-grade reasoning for responsibility weighting and anchor matching. Use `claude-sonnet-*`, `claude-opus-*`, `glm-4.5+`, `gpt-4-class`, or comparable.

---

## License

MIT — see [`LICENSE`](./LICENSE).

## Author

Barry Wang ([@bwancoding](https://github.com/bwancoding))
