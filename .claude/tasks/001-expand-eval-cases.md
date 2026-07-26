# 001 — Three more contrasting pairs in the eval suite

## Goal

Grow `evals/cases/` from 18 cases to 24 by adding three pairs. Each pair differs
in exactly one respect, so a failure names a specific rule rather than a mood.

### Pair 10 — `remote-conflict`

The posting contradicts itself about location. The skill must surface the
contradiction as an open question rather than quietly picking a reading.

- `10a-remote-contradiction` — header says remote-first, a later bullet says five
  days on site. Must not resolve it silently.
- `10b-remote-consistent` — same role, remote stated consistently.

`pair_expect: differ` is **not** appropriate here; both may legitimately land on
an Apply tier. Assert on content instead: 10a must mention the conflict and raise
it under open questions; 10b must not.

### Pair 11 — `requirement-marker`

Whether the must-have / preferred split is marked changes the Candidacy
denominator.

- `11a-no-split-marker` — six requirements, no "nice to have" heading anywhere.
  Per `references/scoring.md`, everything counts as must-have **and the
  assumption must be stated**. Assert the statement appears.
- `11b-explicit-split` — same six, but two sit under an explicit preferred
  heading. Those two must be excluded from the denominator and reported
  separately.

### Pair 12 — `same-posting-two-languages`

The same job, written twice. Language must not move the verdict.

- `12a-dutch` — posting in Dutch
- `12b-english` — the same posting in English, same company, same numbers

`pair_expect: same`. This is the one pair whose failure would be most damaging:
it would mean the skill judges people differently depending on what language
their market posts in.

## Boundary

Edit only:

- `evals/cases/*.md` — six new files
- `evals/README.md` — add the three pairs to the "what a failure means" table

Do not touch `src/`, `evals/fixtures/`, `evals/baselines/`, or `evals/run.py`.

## Acceptance

```bash
./build.sh --check
python3 evals/run.py --dry-run
python3 -c "import importlib.util;s=importlib.util.spec_from_file_location('r','evals/run.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);c=m.load_cases(None);print(len(c));assert len(c)==24,len(c)"
git diff --stat   # only evals/cases/ and evals/README.md may appear
```

## Known traps

- **The fixture persona is Dutch-market.** `evals/fixtures/jd_criteria.md` sets
  `market: "Netherlands, EU-remote"` and `languages: ["English", "Dutch"]`. Pair
  12 must therefore be Dutch/English. A Chinese or Japanese posting would fail
  for the right reason in the wrong way — the location gate, not the language
  handling.
- **Both members of a pair need `pair_expect`,** or the harness silently skips
  the pair and still prints a clean score. Pair 10 uses no `pair_expect` by
  design; say so in a comment so it does not look like an oversight.
- **`must_match` entries are regexes, matched case-insensitively.** Do not pin
  the casing of a verdict token, and escape anything regex-significant.
- **Do not run `./evals/run.py` without `--dry-run`.** A full run costs real API
  calls and burns a five-hour quota window. Writing cases needs neither.
- Existing cases are the format reference. `05a-comp-basis-mismatch.md` shows
  front matter with `expect_action`, `pair`, `pair_expect`, `must_match`.
- New cases must keep the numbering and naming convention: `NNx-short-slug.md`,
  with an `id:` in the front matter that matches the filename stem.

## Not in scope

Running the suite, recording a baseline, or changing any assertion on the
existing 18 cases. If a new case appears to reveal a defect in `src/`, stop and
report it — changing a scoring rule is a judgement call, not part of this task.
