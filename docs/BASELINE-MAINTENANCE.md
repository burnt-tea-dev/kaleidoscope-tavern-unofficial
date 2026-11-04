# Baseline maintenance

1. Implement gameplay, rendering, guide and API fixes in canonical runtime. Verified Beta APIs and creator experiments are allowed under the owner's current policy; declare their actual engine and experiment requirements. Do not patch fixes during packaging or installation.
2. Bump the release version whenever any exported file changes. Update paired manifests, module versions, guide/payload version and dependencies together.
3. Update `baseline.json` dependencies from verified upstream file metadata. Never infer UUIDs from a version label.
4. Run the repository's functional regressions. Stage reviewed source files, then run `python tools/baseline_gate.py freeze`. An existing version cannot be assigned new content.
5. Review and commit the lock/history. `python tools/baseline_gate.py check --release` and the real packager must pass from a clean commit.
6. Build the candidate from committed sources and pinned author inputs. Follow the current [family update workflow](../family/UPDATE-WORKFLOW.md#擁有者簡化規則2026-11-04) for functional evidence, advisory family differences and deployment.
7. Use the shared latest complete backup, validate the same stopped-world copy, install and read back the tested candidate through the canonical updater. Do not request repeated deployment permission; tooling or documentation changes with unchanged runtime need no game release or restart.
8. Third-party defects require a clean latest-version reproduction and an author feedback record. Temporary fixes need reviewed hashes and a removal condition. Translation must not hide runtime replacements.

Historical artifacts and branches are evidence, not release input. A PR being closed or merged does not prove its content survives in the resulting tree. Reconcile by behaviour and verify the resulting source/export.

Development `check` permits unfrozen runtime edits while retaining structural and append-only history checks. `check --release` always adds frozen identity and clean-commit checks; `--archive` also requires frozen identity. Installable CI archives and family assembly use these strict boundaries. `--identity` can check an unfinished worktree without requiring a clean commit; it is never needed as a second opt-in at a release boundary.

Family operations and integration tooling: `casama233/kaleidoscope-tavern-unofficial/family/MAINTENANCE.md`.

Release freeze now claims the version and exact runtime trees in Git’s shared common directory before changing locks. All local worktrees and known remote-tracking histories are checked for collisions. A conflicting or incomplete claim must be preserved for review; choose a new release version instead of deleting or rewriting it. This coordination guard does not replace PR checks or fresh family deployment evidence.

The owner’s 2026-10-06 requirements apply: repairs must reach canonical remote Git; current Java releases drive adaptation; source/version pinning never establishes full Java parity. Reuse exact unchanged functional evidence and keep only integrity checks at meaningful state transitions. Private integration stays private.
