# T205 recipient session QA observer

This is QA tooling, not a runtime export. Do not add it to LIVE or start another
world. Keep the common owner's existing saved-world first-load/restart gate
unchanged, with the selected T205 and its canonically paired World Liquor source.
Run this observer in a separate functional phase on that same QA copy **after**
the gate (for example, its next normal start), or the existing equivalent
isolated staging. Network logins create player records: they must not run
inside the before/after player-record comparison. Never weaken that comparison,
remove real records, rerun a valid gate, or install the QA database onto LIVE.

Copy `observer.js` to W's QA `BP/scripts/foundation-recipient-session-qa.js` and
select that as W's QA script entry. It imports W's unchanged `main.js`, actual
foundation registration and the same SDK instance used by W's normal consumer.
Keep T's runtime/publisher untouched. No fake lifecycle events, authority rows,
flight grants, inventory or gameplay supplies are injected.

Start with zero players. Send `scriptevent tavern_qa:session_begin {}` once.
The bounded observer emits these markers:

1. `TAVERN_QA_SESSION_LOGIN_READY`: real W registration is ready; start the
   existing `qa-network-player` driver (both fixed names/UUIDs).
2. `TAVERN_QA_SESSION_DISCONNECT_READY {"session":1}`: each first session
   received one empty snapshot, the real SDK accepted it, and ten idle ticks
   passed. SIGTERM the driver and wait for its normal exit.
3. `TAVERN_QA_SESSION_RECONNECT_READY`: native leave events and zero players were
   observed. Start a **new process** with the same two login UUIDs.
4. `TAVERN_QA_SESSION_DISCONNECT_READY {"session":2}`: close the second driver.
5. `TAVERN_QA_SESSION_RESULT`: native IDs, initialSpawn events, per-session empty
   counts, SDK observations, timing and final native player count.

Driver path and resource/network limits come from the existing
`native-network-player-20261106/README.md` in the host work index. Both processes
remain in the same restricted unit/network namespace as the QA BDS; loopback
only, no real account. Observer timeouts also emit a result; the common runner
must still close a remaining driver and stop normally, preserving failures.

`readTavernEffects()=={}` alone cannot prove receipt of an empty snapshot. The
observer also checks `getTavernEffectEntities()` while that received snapshot is
fresh. It creates no duplicate client or cache and calls no internal publisher.

The original bug requires the same native entity ID, a new handle, and a complete
leave/rejoin between two publishes. A normal network reconnect may take longer
or assign another ID. The observer uses the actual snapshot sequence to infer
the unchanged publisher's five-tick phase; boundary ticks are inconclusive.
`pass` requires all four empty/idle/SDK controls plus both critical windows;
otherwise preserve `inconclusive` or the actual failure. A slow successful
reconnect proves its observed session behavior, not that the original race was
exercised. This tool is not a renderer, flight-permission or human-client test.

Prepared verification: JavaScript syntax and diff checks only. No BDS, driver,
saved world, or native reconnect has been run by this source owner. The corrected
placement in the functional phase changes no observer code or exported runtime.
