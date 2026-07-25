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

### `2026-07-25-sonnet-4-6`

Claude Sonnet 4.6, one run per case, 18 cases. The first end-to-end run of the
v1.1 skill.

Recorded against the pre-fix specification, so it is a *baseline*, not a pass:
manual inspection of these very files produced five specification fixes (verdict
token pinned, too-thin action defined, criteria-line placement, semantic domain
matching, `org_fit` neutral case). Cases `08b` and `02a` are the interesting
reads — both surfaced defects that every mechanical assertion missed.

Case `07b` here is the corrected version of the posting; the original tripped the
intensity gate and never reached the decision matrix, so it tested nothing.

## Adding one

Run the suite, then copy each sandbox's `output.txt` into a new dated directory.
Do not edit the files afterwards — a hand-tidied baseline is worthless for
diffing.
