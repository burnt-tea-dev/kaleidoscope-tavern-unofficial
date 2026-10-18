# Canonical organization transfer

On 2026-10-19 the owner confirmed that the four existing repositories moved to
`burnt-tea-dev` (organization ID `344456559`). Their repository IDs remain:

| Repository | ID | Visibility |
| --- | --- | --- |
| kaleidoscope-tavern-unofficial | 1377171148 | public |
| kaleidoscope-grilling-unofficial | 1377218440 | public |
| kaleidoscope-world-liquor-unofficial | 1385218112 | public |
| senluo-family-integration-private | 1406868911 | private |

Current API, Actions and PR checks bind the new name to these original IDs and
visibility. The API owner must also match the organization ID and type.
Historical `casama233/...` runtime source keys, receipts, release history and
previous CI evidence retain their original scope; a redirect alone is not proof
of a current canonical source. Pack UUIDs, exported runtime and release versions
are unchanged by this tooling update.

Explicit cross-repository source gates preserve the original Actions event.
They validate its parent against the same four fixed targets and separately
validate the selected child's reviewed target. A frozen historical child with
no transferred target retains its original baseline identity check.
