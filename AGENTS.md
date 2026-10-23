# AGENTS.md

StarFling is FunKey OS for the Anbernic RG Nano, a Buildroot-based
embedded Linux OS image, tuned for fast boot. It is a fork of
L-K-M/FunKey-OS-Starling (which adds Favorites), itself a fork of the
`rg_nano` branch of DrUm78/FunKey-OS (a fork of FunKey-Project/FunKey-OS).
Keep StarFling's delta readable against upstream and record every
intentional divergence in `docs/starfling/DIVERGENCE.md`.
**The default branch is `master`, not `main`.**

- Builds produce a full OS image under `images/` (~12 GB free disk, 1.5–3 h
  native first build, ~4 h under emulation). `tools/build-local.sh` builds
  the working tree in Docker; `make -s print-artifacts` prints artifact
  names. `buildroot/` is a submodule.
- CI workflows: `build.yml` (full OS build), `build_sdk.yml`, `docker.yml`,
  `release.yml`, `retrofe-patches.yml`, `versions.yml`.
- Version is user-facing in README (e.g. "StarFling 0.1.0") and the
  `FunKey-sdcard-StarFling-*-RG_Nano.img` artifact names. Keep the
  `FunKey-` prefix: installed firmware globs `/mnt/FunKey-*.fwu`.
- Starling 3.1.3 (the same code as StarFling 0.1.0) was verified on K's
  RG Nano on 2026-10-23; see `docs/starfling/DEVLOOP.md` section 6.
  Anything after that is unverified until K tests it: CI green means it
  compiles, not that the screen works. Treat hardware-facing changes
  accordingly (see README "Early days" and "Recovery").

<!-- shared-rules:start -->

## Working practices

- Follow explicit task instructions over the default workflow below.
- Writing the code is not finishing the task. A task is finished when
  its changes are merged to master through a PR that passed CI and that K
  approved, or when K explicitly accepts a different end state.
- Start every task on current code. Fetch first, then cut the task
  branch from origin/master — never from a stale local branch or an old
  checkout. To continue existing work, rebase or merge the latest
  origin/master into it before editing. Never overwrite existing work to
  update.
- Resolve ambiguity before making consequential changes. State low-risk
  assumptions; ask when scope, safety, or expected behavior is unclear.
- Keep changes focused. Do not modify unrelated code, formatting, or comments.
- Prefer surgical edits over whole-file rewrites when the result is equivalent.
- Stage only intended files. Inspect the diff before committing.

## Communication

- Be concise, factual, and direct. Preserve necessary context and uncertainty.
- Avoid praise, motivational filler, emojis, and em dashes in new prose.
- Address the reader directly in user-facing copy.
- Report what was verified and what remains unverified. Never imply that an
  unavailable check passed.

## Code design

- Prefer early returns and shallow nesting. Separate logical blocks with
  blank lines.
- Use descriptive constants or enums for meaningful or repeated values.
  Use existing standard definitions for protocol/specification constants.
  Keep obvious, one-off values inline.
- Use enums for behavioral modes that would otherwise require ambiguous
  boolean arguments.
- Default members to private. Widen visibility only for required consumers,
  and review the change as an API design decision.
- Follow the repository's declared dependency boundaries. UI and controllers
  must use application services rather than directly accessing databases,
  subprocesses, sockets, or other low-level mechanisms.
- Encapsulate low-level mechanics behind domain-oriented interfaces.
- Reuse genuinely shared logic. Avoid speculative abstractions and layers
  that only forward calls.
- Prefer pure functions for business rules and immutable data where practical.
  Isolate side effects; document non-obvious state ownership or synchronization.
- Explain non-obvious intent, constraints, and tradeoffs in comments.
  Do not narrate obvious code. Add examples or diagrams when they clarify it.

## Validation and errors

- Validate untrusted input at entry points. Where practical, represent valid
  states in types and enforce persistent invariants in database schemas.
- Represent absence and failure explicitly.
- Use assertions for internal programming invariants, not external-input
  validation or required runtime error handling.
- Prefer explicit, actionable errors over silent failure or undocumented
  fallback. Document intentional recovery behavior.
- Never report a skipped or failed operation as successful.

## Bug fixes

1. Identify the root cause and define an observable success criterion.
2. Add a regression test and observe the relevant failure before fixing it.
3. Implement the fix and observe the test passing.
4. Check surrounding behavior for regressions and architectural consistency.

If an automated regression test is impractical, document the reproduction
and verification procedure. State any inability to reproduce the failure.

## Verification

- Run relevant tests and lint after changes.
- Choose coverage by affected behavior and risk, not patch size.
- Use integration or end-to-end tests for critical workflows and boundaries;
  test isolated business rules at the lowest effective level.
- Run broader suites for cross-cutting or high-risk changes, and the full
  required release checks before releasing.
- Validate the requested command, options, platform, and configuration.
  Unrelated green CI is not proof that the reported problem is fixed.
- Recheck after the final edit. Distinguish local checks from CI results.

## Commit messages

- Use a capitalized, imperative subject without a final period.
- Target 50 characters; never exceed 72.
- Separate the subject and body with one blank line.
- Wrap body text at 72 characters.
- Explain what changed and why. Leave implementation mechanics to the code.

## Implementation and review

Unless explicitly instructed otherwise:

1. Work on a focused branch cut from the latest origin/master and open a PR
   against master before reporting the task as done.
2. Inspect CI results for the latest commit. Fix failures caused by the
   change; report unrelated or infrastructure failures rather than
   working around them.
3. Merge only when K has approved merging for the task and required checks
   pass on the latest commit. Otherwise report the PR as ready and ask K.

## Ending a task

- A task ends with its changes merged to master, not with code written
  and not with a PR merely opened.
- Never finish with uncommitted changes or unpushed commits in the
  worktree. Commit, push, and open or update the PR first.
- If a step is impossible (missing push access, CI failure), report the
  exact blocker instead. Never present unmerged work as finished.
- Before finishing, confirm: the requested behavior is implemented
  without unrelated changes; relevant checks pass on the latest code;
  remaining risks and validation gaps are disclosed.
- The final response states where the work stands: branch, PR, CI
  status, and whether it is merged.
