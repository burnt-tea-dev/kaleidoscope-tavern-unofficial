# Canonical validation

All validation jobs share `.github/workflows/validation.yml`. Feature branches
run through pull requests; `main` also has a push run. New commits cancel older
runs for the same pull request or branch. Publication remains separate.
The development entry is the [family workflow](../family/UPDATE-WORKFLOW.md);
this document describes the executable CI checks it calls.

The `impact` job reads the complete pull-request diff or the entire main push
range once. It includes deleted paths and both sides of renames. An unavailable
comparison, unknown event or unknown path selects both runtime and family checks.
The job runs the existing classifier tests before
publishing its decision and paths, so skipped work remains reviewable.

| Changed input | Validation |
| --- | --- |
| Ordinary Markdown in `docs/`, top-level family instructions or named root documentation | Impact and baseline |
| Family lock/feedback or registered family tools, including `tools/family_update.py` and its package | Impact and baseline, including existing family regressions |
| Only known pack exports under `runtime/BP/` or `runtime/RP/` | Impact, baseline, package, mechanics and scripts; family regressions also run if other affected inputs require them |
| Tests, fixtures, other tools, data, SDK, art, dependency/CI configuration, baseline/release history, packaged release notes or an unrecognised path | Runtime checks and family regressions |
| Manual dispatch or unavailable change comparison | Runtime and family checks; specialized jobs run only on manual dispatch |

This is an explicit input classification, not a blanket file-extension filter.
For example, `tools/fixtures/reference.md` and packaged
`docs/RELEASE-NOTES-*.md` still select both runtime and family checks. Family orchestration fixtures
select the family-update regression discovery. New family tools must be
registered with their existing coverage to use the family-only route. Unknown
tools, transitive helpers and workflow changes conservatively run both suites;
they cannot bypass family coverage by being absent from the registered list.

`baseline` checks release/history identity, minimal dependency and release-claim
regressions, the publication request and session observer callbacks. Its family
step runs for family/shared inputs, manual dispatch or unavailable classification:
the existing update-orchestrator discovery plus bundle, guard, saved-world and
both upstream-watch suites. A failed classifier or missing output cannot skip
that step; `baseline` still runs unless the workflow is cancelled. These are
offline regressions and do not start BDS or contact LIVE.

`historical-baseline`, `bridge`, `catalog`, `audit`, `efficiency`, `foundation`,
`glassware-hit-basis` and `native-persistence` are manual-only diagnostics.
They retain their pinned Java/peer/baseline revisions and evidence. Automatic
runtime jobs use explicit conditions, so inexpensive changes complete with
skipped jobs rather than hanging behind workflow path filters. Each identical
check has one owner:

- `baseline` owns the family suites and release identity/claim/publication checks;
  manual historical checks do not repeat them. Historical bridge regressions and
  Windows Dash compilation retain their distinct project/export coverage.
- `catalog` owns the paired creative catalog test; `foundation` retains the
  distinct cross-pack adapter and effect tests.
- `glassware-hit-basis` owns the pure hit-basis tests; `scripts` retains pickup
  core and adapter tests.
- `mechanics` owns the tap transaction suite. The duplicate manual `tap-carriers`
  job is retired; the existing mechanics artifact includes its results.
- `package` reproduces storage geometry and rejects drift, then runs
  `check_release.py --java-source ... --baseline ...` once. That aggregate
  command passes the pins to both source checks and writes the same storage and
  launch evidence. Its no-argument local entrypoint still runs every check.

The effect-bar test in `foundation` remains because its `LIQUOR_SOURCE` enables
a cross-pack case that the standalone package check does not exercise.

To inspect a prospective change locally:

```sh
python tools/ci_impact.py --paths family/upstream.lock.json docs/BASELINE-MAINTENANCE.md
python tools/test_ci_impact.py
```

The `native-persistence` job may verify an earlier native run instead of creating
another disposable world when every execution input is unchanged. Selection is
bounded to recent runs of this canonical repository and workflow. The original
native job and its actual execution steps must have succeeded, even if an
unrelated job made that workflow fail. Reuse checks the source checkout identity,
complete paired runtime and baseline, native runner/observer/validator inputs,
original artifact digest and complete first/restart logs. The existing recorder
validators still check the observations. A separately recorded reuse proof binds
the current source to those unchanged inputs; the original reports, source
commits and failed workflow outcome are never rewritten. Missing equivalent
inputs select a fresh run. Invalid selected evidence fails the job rather than
silently falling back to another run. Reused jobs cannot serve as original native
runs, and this does not replace a deployment's fresh saved-world rehearsal.

CI results remain scoped to what each suite actually verifies. Script doubles
and native BDS loading do not provide human-client rendering acceptance. Family
deployment still requires the canonical candidate receipt, actual native and
saved-world evidence, and the deployment admission procedure.
