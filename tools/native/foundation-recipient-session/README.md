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

## Existing runner and verified network setup

Use the existing driver/helper in
`/root/senluo-baseline-20260930/java-parity-20261105/native-network-player-20261106/`.
Its README owns the current connection setup. BDS1.26.60.6's G
`native-ice-interface-r4` has reached ICE/DTLS/SCTP/login/initialSpawn with this
setup and then closed both clients normally. That establishes the connection
path only; its G gameplay result is not T205 session evidence.

Keep the existing resource limits and identity verification. HTTP signaling
still uses `http://127.0.0.1:QA_PORT`; ICE also uses the single address
`192.0.2.62/32` inside the closed namespace. Pass the helper's
`SYSTEMD_NETWORK_PROPERTIES` as separate systemd arguments:

```sh
--property=PrivateNetwork=yes --property=IPAddressDeny=any \
--property=IPAddressAllow=localhost --property=IPAddressAllow=192.0.2.62/32
```

Inside that unit, enable loopback through the existing runner, then call
`prepare_ice_interface(unit)` **once before starting BDS**. The helper creates
`qaice0` and `qaice1` in that same namespace; only qaice0 receives the /32.
There is no host/other-namespace link or default route. Controller, BDS and both
successive driver processes remain in the same unit/cgroup/network namespace.
Keep the existing QA settings (`online-mode=false`, `allow-list=false`,
`max-players=2`) and the driver's fixed names/UUIDs.

## Two successive sessions on the same BDS

Start with zero players. Send `scriptevent tavern_qa:session_begin {}` once.
The bounded observer emits these markers:

1. `TAVERN_QA_SESSION_LOGIN_READY`: real W registration is ready; start the
   first process with `start_network_players(bds_pid, unit, session_1_log, port)`
   (both fixed names/UUIDs). Keep its returned process and stream.
2. `TAVERN_QA_SESSION_DISCONNECT_READY {"session":1}`: each first session
   received one empty snapshot, the real SDK accepted it, and ten idle ticks
   passed. Call `stop_network_players(process, stream)` to send SIGTERM and wait
   for normal exit; retain its `forced` and `returncode` results.
3. `TAVERN_QA_SESSION_RECONNECT_READY`: native leave events and zero players were
   observed. On the same running BDS, call `start_network_players` again with a
   **new process and a different, unused `session_2_log`**, using the same unit,
   port, names and login UUIDs.
4. `TAVERN_QA_SESSION_DISCONNECT_READY {"session":2}`: normally close the second
   process with its own returned process/stream through `stop_network_players`.
5. `TAVERN_QA_SESSION_RESULT`: native IDs, initialSpawn events, per-session empty
   counts, SDK observations, timing and final native player count.

Use distinct paths such as `session-1.log` and `session-2.log` under this QA's
evidence directory. The helper opens logs with `open('x')`: reusing round one's
path fails instead of overwriting it. Both log files remain available for
`spawned_names(log_path)` and raw transport observations. Do not restart BDS or
prepare its ICE interfaces again between rounds.

Record both normal driver exits (`forced=false`, `returncode=0`), native leaves
and final playersAfter=0 before normally stopping BDS. Observer timeouts also
emit a result; the common runner must still close a remaining driver and stop
normally, preserving the original result and any nonzero player count.

## Evidence boundary

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

Each session records its own `leaveTick` only when its native leave arrives.
The prior row's leave time is read directly for the critical-window calculation;
copying it onto a new row incorrectly marks that new session as already offline.

The real-module callback regression runs the observer and actual foundation SDK
with fixture Native events/time/player handles and W registration:

```sh
node --experimental-vm-modules --test tools/native/foundation-recipient-session/observer.test.mjs
```

It covers second-session empty/SDK receipt and its own leave, different IDs with
valid controls but an inconclusive result, and a reconnect crossing a publish.
All three failed before removing the inherited leave time and pass after it;
these fixture outcomes are not Native PASS. The original r3 Native timeout/fail
remains unchanged and requires a separate run by the common owner to reassess.
No exported runtime, publisher, SDK, timing rule or status threshold changes.
