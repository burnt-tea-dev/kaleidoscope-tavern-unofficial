# Native first-message timing probe

This is an isolated QA fixture using the Beta GameTest experiment/API. For an engine-only baseline, enable only this behavior pack in a disposable QA copy. Record the engine version and actual resolved pack stack: resource-pack dependencies can enable other behavior packs. This is not a family release or runtime change.

The simulated player waits two ticks after spawning. The test records the actual player location, measures two synchronous `sendMessage` calls with the short owned message, records returned/exception outcomes, and disconnects the player in `runOnFinish`.

A successful send call means only that the API call returned without throwing. It does not prove good performance or that a real player saw the message rendered. Do not treat a warmed second call as a fix for the first-call delay.

After enabling the fixture and loading its test area in isolated QA, run:

```mcfunction
gametest run senluo_message_diag:simplayer_first_message 0
```

The `SENLUO_FAMILY_GT` records use the existing GameTest parser. Their explicit diagnostic limits do not grant family admission. Never install this fixture or spawn its player on LIVE.

To compare an actual client's first call, restart the isolated world/process and have that player run this command **before** any GameTest or other probe message:

```mcfunction
scriptevent senluo_message_diag:player_message
```

Capture the two visible messages, original timing log, client and engine builds, resolved pack stack and whether the caller was an actual client or a simulated player. The handler deliberately records only `command_source_player`; that event alone cannot prove a real player participated. Restart again before measuring the simulated-player route, so one route does not warm the other.

Observed on 2026-11-01 with BDS 1.26.60.6, this exact fixture in an isolated saved-world copy returned in 176 ms on the first simulated-player send and under 1 ms on the second. The call/cleanup checks passed; the first-call delay remains. The command-source actual-client route is pending human verification.
