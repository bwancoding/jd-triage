# Baselines

A recorded reference run: one verbatim output per case, from a named model on a
named date. Committed on purpose.

Their value is comparison. A case that fails on a cheaper model but passed here is
a **model-capability** signal; a case that fails on both is a **specification**
defect. Without a baseline those two look identical, and you end up rewriting a
rule that was fine.

```
evals/baselines/<date>-<model>/<case-id>.txt
```

## Runs on record

### `2026-07-26-glm-5.2` — current reference

GLM-5.2 via Volcengine, one run per case, 18 cases, against the shipped v1.1
specification. 18/18 rule-compliant, 6/6 pairs separated correctly.

**Diff this one.** It is the first baseline recorded after every known
specification defect was fixed, so a future divergence from it is a signal rather
than a known-stale difference.

Four verdicts differ from the Sonnet run below. Three are explained by the
specification changes between them; one is not:

| Case | Sonnet (pre-fix) | GLM-5.2 (post-fix) | Why |
|---|---|---|---|
| `01b-redline-tail` | `Apply now` | `CONDITIONAL` | **Not a spec change.** The responsibility-weight rule was identical in both runs; a red line in a tail support bullet must produce CONDITIONAL. Sonnet's output never mentions the red line at all. GLM-5.2 is correct here |
| `08b-dense` | `Backup` | `Apply now` | Semantic domain matching and the `org_fit` neutral case — both added after the Sonnet run. Domain 2★→5★, Org 1★→3★ |
| `03a-anchor-known` | `Apply` | `Apply now` | Tier boundary; both cite their anchor correctly, which is what the case tests |
| `03b-anchor-fictional` | `Apply` | `Apply now` | Same |

The remaining 14 agree.

### `2026-07-25-sonnet-4-6` — historical starting point

Claude Sonnet 4.6, one run per case, 18 cases. The first end-to-end run of the
v1.1 skill.

Recorded against the **pre-fix** specification, so it is a starting point, not a
pass — and **not a like-for-like model comparison**, since the specification moved
underneath it. Manual inspection of these very files produced five of the six
specification fixes (verdict token pinned, too-thin action defined, criteria-line
placement, semantic domain matching, `org_fit` neutral case). Cases `08b` and
`02a` are the interesting reads: both surfaced defects that every mechanical
assertion had passed.

Keep it for that history. Diff against `2026-07-26-glm-5.2` instead.

Case `07b` here is the corrected version of the posting; the original tripped the
intensity gate and never reached the decision matrix, so it tested nothing.

## Adding one

Run the suite, then copy each sandbox's `output.txt` into a new dated directory.
Do not edit the files afterwards — a hand-tidied baseline is worthless for
diffing.
