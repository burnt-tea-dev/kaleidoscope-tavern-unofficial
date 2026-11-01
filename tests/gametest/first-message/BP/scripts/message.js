import { GameMode, system } from "@minecraft/server";
import * as GameTest from "@minecraft/server-gametest";

const NS = "senluo_message_diag";
const TEST_ID = `${NS}:simplayer_first_message`;
// Reuse the existing family GameTest record parser; limits still mark this as diagnostic only.
const PREFIX = "SENLUO_FAMILY_GT ";
const MESSAGE = "Native first-message timing probe.";
let active;
let player;
let result;

function emit(kind, data = {}) {
  console.warn(PREFIX + JSON.stringify({ schema: 1, run_id: active.runId, test: TEST_ID, kind, ...data }));
}

function timedSend(target, label) {
  const start = Date.now();
  try {
    target.sendMessage(MESSAGE);
    const elapsedMs = Date.now() - start;
    console.warn("[Native first-message timing probe] " + JSON.stringify({ label, elapsedMs, threw: false }));
    return { elapsedMs, threw: false, error: null };
  } catch (error) {
    const elapsedMs = Date.now() - start;
    const message = String(error);
    console.warn("[Native first-message timing probe] " + JSON.stringify({ label, elapsedMs, threw: true, error: message }));
    return { elapsedMs, threw: true, error: message };
  }
}

// An actual client can invoke this route before any GameTest player warms this pack's API.
system.afterEvents.scriptEventReceive.subscribe(event => {
  if (event.id !== `${NS}:player_message`) return;
  const target = event.sourceEntity;
  if (target?.typeId !== "minecraft:player") return;
  const first = timedSend(target, "commandSourceFirstMessage");
  const second = timedSend(target, "commandSourceSecondSameMessage");
  console.warn("[Native first-message caller] " + JSON.stringify({
    mode: "command_source_player", first, second,
    limits: { client: false, realPlayerConfirmed: false, savedWorldFamilyAcceptance: false }
  }));
}, { namespaces: [NS] });

GameTest.registerAsync(NS, TEST_ID.split(":")[1], async test => {
  active = { runId: `${NS}-${system.currentTick}-${Date.now()}` };
  player = undefined;
  result = undefined;
  emit("loaded", { dependencies: { server: "2.7.0", gametest: "1.0.0-beta" } });
  emit("begin");
  test.runOnFinish(() => {
    const cleanupErrors = [];
    if (player) {
      try { player.disconnect(); } catch (error) { cleanupErrors.push(String(error)); }
    }
    emit("finish", {
      completed: result?.pass === true && cleanupErrors.length === 0,
      outcome: result?.pass === true && cleanupErrors.length === 0 ? "pass" : "fail",
      cleanupErrors
    });
  });

  try {
    player = test.spawnSimulatedPlayer({ x: 41, y: 1, z: 45 }, "NativeMessageDiag", GameMode.Survival);
    await test.idle(2);
    const actualPlayerLocation = { ...player.location };
    const first = timedSend(player, "firstMessage");
    const second = timedSend(player, "secondSameMessage");
    const checks = {
      simulatedPlayerCreated: !!player?.id,
      firstMessageReturned: !first.threw,
      secondMessageReturned: !second.threw
    };
    result = {
      pass: Object.values(checks).every(Boolean),
      checks,
      actions: { first, second },
      states: { simulatedPlayerIdPresent: !!player?.id, actualPlayerLocation },
      limits: { client: false, renderedGameplay: false, savedWorldFamilyAcceptance: false }
    };
  } catch (error) {
    result = {
      pass: false,
      checks: { simulatedPlayerCreated: !!player?.id, firstMessageReturned: false, secondMessageReturned: false },
      error: String(error),
      stack: error?.stack ?? null,
      limits: { client: false, renderedGameplay: false, savedWorldFamilyAcceptance: false }
    };
  }

  emit("result", result);
  if (result.pass) test.succeed();
  else test.fail("Native first-message timing probe failed; inspect the preceding result record.");
}).structureName(`${NS}:arena`).structureLocation({ x: 0, y: 80, z: 0 }, "overworld")
  .maxTicks(200).maxAttempts(1).required(true);
