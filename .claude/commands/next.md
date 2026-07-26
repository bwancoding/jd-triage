---
description: Pick up the next queued task from .claude/tasks/ and carry it out
---

Work the oldest unfinished task in `.claude/tasks/`.

1. List `.claude/tasks/*.md`, ignoring `done/`. Take the lowest-numbered file. If
   there are none, say so and stop — do not invent work.
2. Read it in full, then read `CLAUDE.md` at the repo root. Its constraints apply
   and override anything that would be more convenient.
3. Do the work. Stay inside the task's stated boundary and touch nothing outside
   it, however tempting the adjacent cleanup looks.
4. Run **every** command under the task's Acceptance section. All must pass. If
   one fails, fix and re-run. Never report success while a command is red, and
   never edit a check to make it agree with the code.
5. On success, `git mv` the task file into `.claude/tasks/done/` and commit the
   work and the move together.
6. Report three things: what changed, the acceptance output, and anything you
   noticed but deliberately did not touch.

Stop and ask instead of guessing when the task is ambiguous, when finishing it
would require one of the decisions listed under **Where judgement is required**
in `CLAUDE.md`, or when the same problem has resisted two attempts — a third
attempt usually means the specification is wrong, not the code.
