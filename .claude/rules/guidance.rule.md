---
paths:
  - "CLAUDE.md"
  - ".claude/**"
  - "sensors/**"
  - "docs/**"
---

# Where Guidance Lives

Guidance for humans and agents is spread across five places on purpose. Before adding or moving a piece
of it, walk this ladder — the first step that fits wins:

1. **Is the mistake interceptable at a single point in time, by an exit code?** → a sensor in
   `sensors/<name>/`, wired in `.claude/settings.json`, with its cases in `tests/test_sensors.py`. A
   hook cannot be forgotten and its message arrives exactly when it is actionable. Reserve prose for
   judgment that no exit code can settle.
2. **Is it a repeatable pattern that any file matching a path must follow?** → a rule in
   `.claude/rules/<topic>.rule.md`, scoped with a `paths` glob.
3. **Is it a repeatable multi-step procedure?** → a skill in `.claude/skills/<name>/SKILL.md`, with a
   `references/` file for what only some invocations need.
4. **Is it needed in every session — commands, the architecture map, *when* to do something?** →
   `CLAUDE.md`. Everything there costs context on every turn; keep it short.
5. **Is it for a human running the demo or reading the project?** → `README.md` or `docs/`, in English.

The operative test is **audience**: who needs to read this, and where are they when they need it? A
rule is read by an agent at the moment it touches a matching path.

## How much to write

Say the rule, and the criterion that settles a borderline case. Two tests, in order:

- Is it restating mechanism the code already carries — a signature, a layout, what a call does? → cut it.
- Would a reader **undo** the decision, because the change reads as an obvious improvement? → it has to
  be written, in one sentence.

Rule and code must never contradict each other. Where one is written and the code diverges, that is a
finding to raise: one of the two is stale, and which one is not a guess to make silently.

## Writing a rule

- Name it `<topic>.rule.md` and open with one sentence of scope.
- A rule loads when a matching file is read. Point to other files only when they will not be loaded at
  that moment — never back to `CLAUDE.md`, which is always present.

## Changing a definition

When a term changes meaning, enumerate every occurrence of it — in the file, then in the sibling rules,
skills, sensor messages and `CLAUDE.md` — and classify each as a definition or a mention. Then sweep the
**concept** too: a stale copy may name neither the term nor the wording. Sweep the examples with the
definitions, then run the new criterion against the code it governs.

## Moving guidance

Move by audience, not by subject. Delete what the destination already says instead of migrating it — a
migration that keeps both copies creates the drift it was meant to prevent. A sensor is the one guide
tracked mechanically: `tests/test_sensors.py` fails when `sensors/<name>/` is not wired or has no `.md`.
