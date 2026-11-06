# Tavern 0.6.205

A player leaving and reconnecting with the same entity ID between publisher
passes could miss the new session's initial empty authority snapshot. The
publisher now drops only that player's delivery cache on leave and initial
spawn. Other idle recipients keep their deduplication; ordinary respawns do not
reset it. Active-row heartbeat, transport framing, SDK and saved data are unchanged.

The actual publisher regression fails before the fix and passes after it,
including same-ID/new-handle reconnect, independent initial-spawn invalidation,
ordinary respawn and idle-peer isolation. The affected foundation/SDK suite
passes128 tests. These use Native API boundary fixtures, not an observed native
rapid reconnect. No BDS or LIVE action was needed for this source fix.
