# Tavern 0.6.179 — retained transparency and corrected effect retirement

This candidate retains the ordinary-ice transparency and initial online countdown repairs described in [T178](RELEASE-NOTES-0.6.178.md), and corrects the empty-state boundary found by its full CI. T178's original release identity and failed workflow remain preserved; that candidate was not merged or deployed.

The first successful read creates an online clock only when saved effects contain entries. Reading an expired or empty mob status therefore does not revive a retired track. The existing Bloody Mary test detected this defect after an effect expired and another kill checked its status; that assertion remains unchanged.

All six focused clock cases, the four existing Bloody Mary adapter cases and the 56-test efficiency suite pass on this source. The barrel-material implementation is unchanged from its independently reviewed 66-test result. Full required CI remains authoritative for the complete candidate.

The exact companion is World Liquor 0.1.156, retaining its freezer blue-dye sprite and deferred interaction repairs. Full-family static checks, a fresh consistent saved-world first load/restart, admission and deployment are still required. Client transparency ordering, lighting and actual interaction acceptance remain pending: `client=false`, `production_ready=false`, `pending_client_acceptance`.
