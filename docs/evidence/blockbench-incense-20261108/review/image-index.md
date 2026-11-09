# Image captions and framing review

All 24 original 1364×1024 JPEGs were individually inspected. Files were copied byte-for-byte, never cropped, annotated, recompressed or recreated. Candidate evidence consists of 13 captures; 11 earlier captures are baseline failure evidence. SHA256 values below identify exact raw files.

Camera-dependent order is explicit in every entry. Scene hashes bind each image to the preserved scene input; screenshots alone do not independently attest those hashes.

## 1. candidate/evidence/catnip-closed-bottom.jpg
- Original file: [Open raw JPEG](candidate/evidence/catnip-closed-bottom.jpg).
- Caption: Catnip closed underside. Source left and candidate right have the matching purple centre; current middle exposes the brown lid. All three pots fully visible.
- Scene: `candidate/scenes/catnip-closed-source-current-candidate.bbmodel`
- Framing: Three separated pot footprints, approximately 120 pixels wide, fully framed.
- Limit: BOTTOM hides the upper geometry and cannot by itself distinguish the closed/open top state.
- Raw JPEG SHA256: `9add7dec996eb292ac4a1e51208cf2a33ad355d0eb450a5efc0c49e1943466ac`
- Scene SHA256: `3d8f65982e8e7afb86c77f74264550be309d6533f69f429e5d0d09cbea376b39`

## 2. candidate/evidence/catnip-closed-perspective.jpg
- Original file: [Open raw JPEG](candidate/evidence/catnip-closed-perspective.jpg).
- Caption: Catnip closed, default perspective. Candidate screen-left, current middle, source right. All three complete models are visible; tops, foliage and base outlines retain their appearance.
- Scene: `candidate/scenes/catnip-closed-source-current-candidate.bbmodel`
- Framing: All three complete models and foliage tips fully within viewport, with clear separation.
- Limit: Underside is naturally hidden; this view checks visible preservation only.
- Raw JPEG SHA256: `aaa45808ef5ed007e6e9cb2d9a92e8b430205c61220b22484da1edcf7fd67506`
- Scene SHA256: `3d8f65982e8e7afb86c77f74264550be309d6533f69f429e5d0d09cbea376b39`

## 3. candidate/evidence/catnip-closed-tilted-bottom.jpg
- Original file: [Open raw JPEG](candidate/evidence/catnip-closed-tilted-bottom.jpg).
- Caption: Catnip closed, shallow orbit from BOTTOM. Source left and candidate right retain purple undersides; current middle exposes brown. All three pots fully visible.
- Scene: `candidate/scenes/catnip-closed-source-current-candidate.bbmodel`
- Framing: All three enlarged pots, base rims and adjacent foliage within viewport. A small green mark is visible near the current model; origin was not diagnosed, and it is not used as defect evidence.
- Limit: Unmeasured manual gizmo orbit; no exact angle is claimed. The green mark and perspective lighting are not used for pixel comparisons.
- Raw JPEG SHA256: `612f92436a10e18c38bb0bdb4248737ee15dec023adca21687be358c3ecf4b23`
- Scene SHA256: `3d8f65982e8e7afb86c77f74264550be309d6533f69f429e5d0d09cbea376b39`

## 4. candidate/evidence/catnip-open-bottom.jpg
- Original file: [Open raw JPEG](candidate/evidence/catnip-open-bottom.jpg).
- Caption: Catnip open underside. Source left and candidate right have the matching purple centre; current middle exposes the brown lid. All three pots fully visible.
- Scene: `candidate/scenes/catnip-open-source-current-candidate.bbmodel`
- Framing: Three separated pot footprints, approximately 120 pixels wide, fully framed.
- Limit: BOTTOM hides the upper geometry and cannot by itself distinguish the closed/open top state.
- Raw JPEG SHA256: `6ba092dcd2905c3b22ab2f050f3d5c75bec68305da4701c745a2bad5be7386e7`
- Scene SHA256: `f26968c4b8f149e93d4068e3bb08aaaf15a2f4b4376d7b729e2525dd12db0607`

## 5. candidate/evidence/catnip-open-perspective.jpg
- Original file: [Open raw JPEG](candidate/evidence/catnip-open-perspective.jpg).
- Caption: Catnip open, default perspective. Candidate screen-left, current middle, source right. All three complete models are visible; tops, foliage and base outlines retain their appearance.
- Scene: `candidate/scenes/catnip-open-source-current-candidate.bbmodel`
- Framing: All three complete models and foliage tips fully within viewport, with clear separation.
- Limit: Underside is naturally hidden; this view checks visible preservation only.
- Raw JPEG SHA256: `299b8ade2eae895e05c565c4db41f59fb5732166f7ad5b7fb7f07a46a163447b`
- Scene SHA256: `f26968c4b8f149e93d4068e3bb08aaaf15a2f4b4376d7b729e2525dd12db0607`

## 6. candidate/evidence/incense-all16-triplets-1-bottom.jpg
- Original file: [Open raw JPEG](candidate/evidence/incense-all16-triplets-1-bottom.jpg).
- Caption: Butterfly and Catnip, closed/open. Top to bottom: catnip open; catnip closed; butterfly open; butterfly closed. Left to right: source, current, candidate. All four triplet rows are visible. Source/candidate centre patterns agree; current differs.
- Scene: `candidate/scenes/incense-all16-triplets-1.bbmodel`
- Framing: All 12 underside squares fully within viewport, with margin. Four rows clear and separate.
- Limit: Approximately 48-pixel-wide pot footprints; adequate for the missing-bottom colour/pattern comparison, not pixel-perfect UV acceptance or fine side details.
- Raw JPEG SHA256: `5c08359574471b54e5bb0f3f3d72e891aff90156451fe81b544575f1a435474c`
- Scene SHA256: `1130c510626ea193554e79b2844a62825bce859e0f4d982a1f3461d2dd1aa2ab`

## 7. candidate/evidence/incense-all16-triplets-1-perspective.jpg
- Original file: [Open raw JPEG](candidate/evidence/incense-all16-triplets-1-perspective.jpg).
- Caption: Butterfly and Catnip, closed/open overview. Each world-X triplet appears candidate/current/source from screen-left to right. All 12 models are present; visible outlines, foliage and top colours show no new candidate/source mismatch.
- Scene: `candidate/scenes/incense-all16-triplets-1.bbmodel`
- Framing: All 12 models fully within viewport, with margin. Perspective depth makes rows diagonal and some foliage overlaps.
- Limit: Overview only: small projected models and partial foliage overlap prevent an exhaustive all-face or pixel-level verdict.
- Raw JPEG SHA256: `477555a6cb85eec5a4be90fa975f56181b557d66d9dc50781bc8970a537177a0`
- Scene SHA256: `1130c510626ea193554e79b2844a62825bce859e0f4d982a1f3461d2dd1aa2ab`

## 8. candidate/evidence/incense-all16-triplets-2-bottom.jpg
- Original file: [Open raw JPEG](candidate/evidence/incense-all16-triplets-2-bottom.jpg).
- Caption: Firefly and Ginkgo, closed/open. Top to bottom: ginkgo open; ginkgo closed; firefly open; firefly closed. Left to right: source, current, candidate. All four triplet rows are visible. Source/candidate centre patterns agree; current differs.
- Scene: `candidate/scenes/incense-all16-triplets-2.bbmodel`
- Framing: All 12 underside squares fully within viewport, with margin. Four rows clear and separate.
- Limit: Approximately 48-pixel-wide pot footprints; adequate for the missing-bottom colour/pattern comparison, not pixel-perfect UV acceptance or fine side details.
- Raw JPEG SHA256: `8c6468095639826bfb92fe88ed2c2874b79af38d4cfea1939a4b0a7aa51c18e2`
- Scene SHA256: `c722d7a0d6f0b59429e5d9bf8277d44c981b3826efaab2a1d7637a7b12db018b`

## 9. candidate/evidence/incense-all16-triplets-2-perspective.jpg
- Original file: [Open raw JPEG](candidate/evidence/incense-all16-triplets-2-perspective.jpg).
- Caption: Firefly and Ginkgo, closed/open overview. Each world-X triplet appears candidate/current/source from screen-left to right. All 12 models are present; visible outlines, foliage and top colours show no new candidate/source mismatch.
- Scene: `candidate/scenes/incense-all16-triplets-2.bbmodel`
- Framing: All 12 models fully within viewport, with margin. Perspective depth makes rows diagonal and some foliage overlaps.
- Limit: Overview only: small projected models and partial foliage overlap prevent an exhaustive all-face or pixel-level verdict.
- Raw JPEG SHA256: `4fbefa0758705de9682e03bb4b1b46fcbfd15a0b32b0cd20fac32543fe318544`
- Scene SHA256: `c722d7a0d6f0b59429e5d9bf8277d44c981b3826efaab2a1d7637a7b12db018b`

## 10. candidate/evidence/incense-all16-triplets-3-bottom.jpg
- Original file: [Open raw JPEG](candidate/evidence/incense-all16-triplets-3-bottom.jpg).
- Caption: Pine and Sakura, closed/open. Top to bottom: sakura open; sakura closed; pine open; pine closed. Left to right: source, current, candidate. All four triplet rows are visible. Source/candidate centre patterns agree; current differs.
- Scene: `candidate/scenes/incense-all16-triplets-3.bbmodel`
- Framing: All 12 underside squares fully within viewport, with margin. Four rows clear and separate.
- Limit: Approximately 48-pixel-wide pot footprints; adequate for the missing-bottom colour/pattern comparison, not pixel-perfect UV acceptance or fine side details.
- Raw JPEG SHA256: `e183aa811324874aaf37831c493c5a0f1a1aade18a23cb2826c8cbab32c0b9b1`
- Scene SHA256: `cb5cee1ac54cb34f0b64a266ed091d109461dd18a889447824efc20e092966ec`

## 11. candidate/evidence/incense-all16-triplets-3-perspective.jpg
- Original file: [Open raw JPEG](candidate/evidence/incense-all16-triplets-3-perspective.jpg).
- Caption: Pine and Sakura, closed/open overview. Each world-X triplet appears candidate/current/source from screen-left to right. All 12 models are present; visible outlines, foliage and top colours show no new candidate/source mismatch.
- Scene: `candidate/scenes/incense-all16-triplets-3.bbmodel`
- Framing: All 12 models fully within viewport, with margin. Perspective depth makes rows diagonal and some foliage overlaps.
- Limit: Overview only: small projected models and partial foliage overlap prevent an exhaustive all-face or pixel-level verdict.
- Raw JPEG SHA256: `c73acbe39e50acaa213350ce293b6691c948052ca44b3c1515fc2f030fe9bb81`
- Scene SHA256: `cb5cee1ac54cb34f0b64a266ed091d109461dd18a889447824efc20e092966ec`

## 12. candidate/evidence/incense-all16-triplets-4-bottom.jpg
- Original file: [Open raw JPEG](candidate/evidence/incense-all16-triplets-4-bottom.jpg).
- Caption: Snow and Spore, closed/open. Top to bottom: spore open; spore closed; snow open; snow closed. Left to right: source, current, candidate. All four triplet rows are visible. Source/candidate centre patterns agree; current differs.
- Scene: `candidate/scenes/incense-all16-triplets-4.bbmodel`
- Framing: All 12 underside squares fully within viewport, with margin. Four rows clear and separate.
- Limit: Approximately 48-pixel-wide pot footprints; adequate for the missing-bottom colour/pattern comparison, not pixel-perfect UV acceptance or fine side details.
- Raw JPEG SHA256: `2769394eeeb935dea8e1ad27ac7ea3d207046960f0e31262ccab27b3ed8c5401`
- Scene SHA256: `d6775852cdf72f734daa55ec7028ae1ed79458e93519bb594c9378573eb7b65a`

## 13. candidate/evidence/incense-all16-triplets-4-perspective.jpg
- Original file: [Open raw JPEG](candidate/evidence/incense-all16-triplets-4-perspective.jpg).
- Caption: Snow and Spore, closed/open overview. Each world-X triplet appears candidate/current/source from screen-left to right. All 12 models are present; visible outlines, foliage and top colours show no new candidate/source mismatch.
- Scene: `candidate/scenes/incense-all16-triplets-4.bbmodel`
- Framing: All 12 models fully within viewport, with margin. Perspective depth makes rows diagonal and some foliage overlaps.
- Limit: Overview only: small projected models and partial foliage overlap prevent an exhaustive all-face or pixel-level verdict.
- Raw JPEG SHA256: `7627f98bcf92e34cf5f369a8cfb23b8ebf308fa27f4d9b49062b6238ddfe9d3e`
- Scene SHA256: `d6775852cdf72f734daa55ec7028ae1ed79458e93519bb594c9378573eb7b65a`

## 14. baseline/evidence/catnip-close-bottom.jpg
- Original file: [Open raw JPEG](baseline/evidence/catnip-close-bottom.jpg).
- Caption: Historical Catnip closed underside: source purple on the left, current brown on the right. This is the original failure evidence.
- Scene: `baseline/scenes/catnip-closed-underside-close-pair.bbmodel`
- Framing: Both enlarged pot footprints fully framed and clearly separate.
- Limit: No repaired candidate is present.
- Raw JPEG SHA256: `1b8611dd0d50fe0e3e5de6f2f9e92fee2b802f5d271ba10465f5ebe577d55743`
- Scene SHA256: `7293c8d8640786ffafee34fa86dc8a7234d60ba7c4f1ce9f51f8cfe4106b2365`

## 15. baseline/evidence/catnip-close-perspective.jpg
- Original file: [Open raw JPEG](baseline/evidence/catnip-close-perspective.jpg).
- Caption: Historical Catnip closed perspective: current screen-left, source screen-right. Both complete models remain visible.
- Scene: `baseline/scenes/catnip-closed-underside-close-pair.bbmodel`
- Framing: Both complete models and foliage fully within viewport.
- Limit: No repaired candidate is present; underside is hidden.
- Raw JPEG SHA256: `a55317b00384c5ff18c3b1bb8cbe1d4c18fd74fec643b07c01dc8b5863d907f0`
- Scene SHA256: `7293c8d8640786ffafee34fa86dc8a7234d60ba7c4f1ce9f51f8cfe4106b2365`

## 16. baseline/evidence/catnip-close-tilted-bottom.jpg
- Original file: [Open raw JPEG](baseline/evidence/catnip-close-tilted-bottom.jpg).
- Caption: Historical Catnip closed tilted underside: source left/current right. Purple source versus brown current remains visible at a shallow orbit.
- Scene: `baseline/scenes/catnip-closed-underside-close-pair.bbmodel`
- Framing: Both enlarged pots fully within viewport. A small green mark is visible near the current model; origin was not diagnosed, and it is not used as defect evidence.
- Limit: Unmeasured orbit, not an exact angle. No repaired candidate is present.
- Raw JPEG SHA256: `900fe44e562546c04d184d057098ae8ba09d3eee0bcd152b3a52544100549f45`
- Scene SHA256: `7293c8d8640786ffafee34fa86dc8a7234d60ba7c4f1ce9f51f8cfe4106b2365`

## 17. baseline/evidence/incenses-1-bottom.jpg
- Original file: [Open raw JPEG](baseline/evidence/incenses-1-bottom.jpg).
- Caption: Historical source/current baseline for Butterfly and Catnip. Top row: catnip closed pair then open pair. Bottom row: butterfly closed pair then open pair. Each pair is source left/current right; all four pairs show the underside difference.
- Scene: `baseline/scenes/incenses-1.bbmodel`
- Framing: All eight underside squares are fully within viewport; outer columns have smaller but adequate side margins.
- Limit: Baseline sheets use a two-row/two-pair layout, unlike the candidate four-row triplets. Do not compare screen positions across layouts.
- Raw JPEG SHA256: `5f961e535b5e1e0698eebe221c56021554e43d8e2f6a76030352fee78f6cb5ce`
- Scene SHA256: `a1d526848f7e300fbd19f0689d0e11ef0b40f3d46b76607bea9a77c2544dcb14`

## 18. baseline/evidence/incenses-1-perspective.jpg
- Original file: [Open raw JPEG](baseline/evidence/incenses-1-perspective.jpg).
- Caption: Historical source/current overview for Butterfly and Catnip, closed/open. Each pair appears current screen-left/source screen-right; all eight models are visible.
- Scene: `baseline/scenes/incenses-1.bbmodel`
- Framing: All eight models and foliage tips fully within viewport, with margin.
- Limit: Historical baseline only; not evidence of the repaired candidate. Perspective hides underside.
- Raw JPEG SHA256: `1cd5d89557989bc7986469f6f0c72ed8b6507372b84177e1f3d15aed4b665281`
- Scene SHA256: `a1d526848f7e300fbd19f0689d0e11ef0b40f3d46b76607bea9a77c2544dcb14`

## 19. baseline/evidence/incenses-2-bottom.jpg
- Original file: [Open raw JPEG](baseline/evidence/incenses-2-bottom.jpg).
- Caption: Historical source/current baseline for Firefly and Ginkgo. Top row: ginkgo closed pair then open pair. Bottom row: firefly closed pair then open pair. Each pair is source left/current right; all four pairs show the underside difference.
- Scene: `baseline/scenes/incenses-2.bbmodel`
- Framing: All eight underside squares are fully within viewport; outer columns have smaller but adequate side margins.
- Limit: Baseline sheets use a two-row/two-pair layout, unlike the candidate four-row triplets. Do not compare screen positions across layouts.
- Raw JPEG SHA256: `bba13e74fc888b551b49acffee42668b9ae8effea2894191bd30e2a0a266174d`
- Scene SHA256: `115ba69c1b912daa0b66a303ec1053908602c2d7e5ae9e2518d907edc48997ab`

## 20. baseline/evidence/incenses-2-perspective.jpg
- Original file: [Open raw JPEG](baseline/evidence/incenses-2-perspective.jpg).
- Caption: Historical source/current overview for Firefly and Ginkgo, closed/open. Each pair appears current screen-left/source screen-right; all eight models are visible.
- Scene: `baseline/scenes/incenses-2.bbmodel`
- Framing: All eight models and foliage tips fully within viewport, with margin.
- Limit: Historical baseline only; not evidence of the repaired candidate. Perspective hides underside.
- Raw JPEG SHA256: `06eca31d507b7638b48b764c59dcb53cff1fb8814fd3ae86e837de0b61f80ceb`
- Scene SHA256: `115ba69c1b912daa0b66a303ec1053908602c2d7e5ae9e2518d907edc48997ab`

## 21. baseline/evidence/incenses-3-bottom.jpg
- Original file: [Open raw JPEG](baseline/evidence/incenses-3-bottom.jpg).
- Caption: Historical source/current baseline for Pine and Sakura. Top row: sakura closed pair then open pair. Bottom row: pine closed pair then open pair. Each pair is source left/current right; all four pairs show the underside difference.
- Scene: `baseline/scenes/incenses-3.bbmodel`
- Framing: All eight underside squares are fully within viewport; outer columns have smaller but adequate side margins.
- Limit: Baseline sheets use a two-row/two-pair layout, unlike the candidate four-row triplets. Do not compare screen positions across layouts.
- Raw JPEG SHA256: `c708e414f9cdbdc7e3ee92bb4625f5c1edc3a9477b6f729b775fb21344b26504`
- Scene SHA256: `0ced8907674779737aa7f108c207ef16cd38b2332418ee0fe7035b328aa93269`

## 22. baseline/evidence/incenses-3-perspective.jpg
- Original file: [Open raw JPEG](baseline/evidence/incenses-3-perspective.jpg).
- Caption: Historical source/current overview for Pine and Sakura, closed/open. Each pair appears current screen-left/source screen-right; all eight models are visible.
- Scene: `baseline/scenes/incenses-3.bbmodel`
- Framing: All eight models and foliage tips fully within viewport, with margin.
- Limit: Historical baseline only; not evidence of the repaired candidate. Perspective hides underside.
- Raw JPEG SHA256: `78752442ea90e090a6dd6d13376f046029fdaccca169171790fbf186724c4140`
- Scene SHA256: `0ced8907674779737aa7f108c207ef16cd38b2332418ee0fe7035b328aa93269`

## 23. baseline/evidence/incenses-4-bottom.jpg
- Original file: [Open raw JPEG](baseline/evidence/incenses-4-bottom.jpg).
- Caption: Historical source/current baseline for Snow and Spore. Top row: spore closed pair then open pair. Bottom row: snow closed pair then open pair. Each pair is source left/current right; all four pairs show the underside difference.
- Scene: `baseline/scenes/incenses-4.bbmodel`
- Framing: All eight underside squares are fully within viewport; outer columns have smaller but adequate side margins.
- Limit: Baseline sheets use a two-row/two-pair layout, unlike the candidate four-row triplets. Do not compare screen positions across layouts.
- Raw JPEG SHA256: `c986bb8dbdaf61ae95d3d3a5f843547d04896dc8fa6ae498ceace0ef9a77dc1b`
- Scene SHA256: `307111e69f63e77d8ab9539b2c4da31811b3a706749e1c08537ed0d41955fc87`

## 24. baseline/evidence/incenses-4-perspective.jpg
- Original file: [Open raw JPEG](baseline/evidence/incenses-4-perspective.jpg).
- Caption: Historical source/current overview for Snow and Spore, closed/open. Each pair appears current screen-left/source screen-right; all eight models are visible.
- Scene: `baseline/scenes/incenses-4.bbmodel`
- Framing: All eight models and foliage tips fully within viewport, with margin.
- Limit: Historical baseline only; not evidence of the repaired candidate. Perspective hides underside.
- Raw JPEG SHA256: `c3adb45fd9cf34cb65c4226bc21e20189519588ffd71fecedd0b3763401ab2cf`
- Scene SHA256: `307111e69f63e77d8ab9539b2c4da31811b3a706749e1c08537ed0d41955fc87`
