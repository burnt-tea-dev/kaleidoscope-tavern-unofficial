# Retained owner and salt coexistence

The salt-removal guard used the retained component's version58 as the required
owning manifest version. A dependency-only owning pair59 therefore failed even
when its Fishing dependency was exactly1.2.10058. The source producer's separate
host replay did not exercise this formal assembly boundary.

The assembler now passes source context to `apply_host_extension` for a retained
component that removes a reviewed recipe. The context contains only
`source_root`, `source_commit` and `sources` (the selected peer repository paths).
It is not an admission receipt or permission to change a version.

The formal guard verifies the current clean source and committed baseline, pack
root and source commit, then calls the existing complete retained-component
loader. That loader still checks all370 conserved payload files, original reviewed integration
conservation, exact manifest/dependency changes and actual current file hashes.
Only after this verification does the guard use the owning pair's version. The
component58 profile, Fishing1.2.10058 dependency and original salt recipe hash
remain mandatory. No owning version range or new profile is added.

The existing synthetic370-file fixture now reaches the real
`apply_host_extension` and recipe-removal guard. It covers the valid59/58 pair,
forged context, wrong Fishing dependency, changed physical payload and corrupt
inner conservation, always checking that rejection preserves the host recipe.
The assembler test also checks propagation of the exact context through the
recipe-removal route. Existing direct component admissions retain their checks.

These are tooling and regression-coverage changes. Exported runtime, manifests,
baseline and release history do not change. Original failed candidates remain
failed. Complete-family static, native and saved-world gates remain required for
the subsequent functional deployment; rendered client behavior is unverified.
