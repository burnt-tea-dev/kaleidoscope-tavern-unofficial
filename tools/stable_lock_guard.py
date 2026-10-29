"""Admission checks for the opt-in Senluo stable-lock delivery profile."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import re
from datetime import datetime
from uuid import UUID

TREE_DIGEST_FORMAT = "senluo-pack-tree-v1"
CANONICAL_SOURCE = re.compile(r"^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)@([0-9a-f]{40})$")
THIRD_PARTY_SOURCE = re.compile(
    r"^third-party: as-installed (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}"
    r"(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2}))$"
)
MIN_RESERVE_BYTES = 2 * 1024 ** 3


def _require(condition, message):
    if not condition:
        raise ValueError("Stable-lock admission: " + message)


def _regular_json(reference, label):
    _require(isinstance(reference, dict), label + " reference must be an object")
    path, wanted = reference.get("path"), reference.get("sha256")
    _require(isinstance(path, str) and path and isinstance(wanted, str)
             and re.fullmatch(r"[0-9a-f]{64}", wanted) is not None,
             label + " reference needs path and SHA256")
    target = Path(path)
    _require(target.is_file() and not target.is_symlink(),
             label + " must be a regular file")
    raw = target.read_bytes()
    _require(hashlib.sha256(raw).hexdigest() == wanted, label + " SHA256 mismatch")
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError("Stable-lock admission: invalid " + label + " JSON") from error
    _require(isinstance(value, dict), label + " must contain a JSON object")
    return value, target, wanted


def _valid_tree_ref(pack):
    path = pack.get("path")
    _require(isinstance(path, str) and path and "\\" not in path,
             "lock pack path missing")
    relative = PurePosixPath(path)
    _require(not relative.is_absolute() and ".." not in relative.parts,
             "lock pack path must be relative")
    _require(isinstance(pack.get("sha256"), str)
             and re.fullmatch(r"[0-9a-f]{64}", pack["sha256"]) is not None,
             "invalid lock pack SHA256")


def _validate_lock(lock):
    _require(lock.get("schema") == 1 and type(lock.get("schema")) is int,
             "unsupported stable lock schema")
    _require(isinstance(lock.get("name"), str) and lock["name"].strip(), "lock name missing")
    _require(lock.get("digest_format") == TREE_DIGEST_FORMAT, "unsupported lock digest format")
    observed = lock.get("observed_at")
    _require(isinstance(observed, str), "stable lock observation time missing")
    try:
        _require(datetime.fromisoformat(observed).tzinfo is not None,
                 "stable lock observation time needs a timezone")
    except ValueError as error:
        raise ValueError("Stable-lock admission: invalid stable lock observation time") from error
    status = lock.get("status")
    _require(isinstance(status, dict) and type(status.get("ci")) is bool
             and status.get("ci") is True and type(status.get("staging_smoke")) is bool
             and "staging_human" in status and "live" in status,
             "stable lock status is invalid or CI is not true")
    packs = lock.get("packs")
    _require(isinstance(packs, list) and packs, "stable lock packs missing")
    seen = set()
    slots = {"behavior": 0, "resource": 0}
    for pack in packs:
        _require(isinstance(pack, dict) and pack.get("kind") in slots,
                 "invalid stable lock pack")
        uid = pack.get("uuid")
        _require(isinstance(uid, str), "stable lock UUID missing")
        try:
            _require(str(UUID(uid)) == uid, "stable lock UUID is not canonical")
        except ValueError as error:
            raise ValueError("Stable-lock admission: invalid stable lock UUID") from error
        _require((pack["kind"], uid) not in seen, "duplicate stable lock UUID")
        seen.add((pack["kind"], uid))
        slots[pack["kind"]] += 1
        _require(type(pack.get("slot")) is int and pack["slot"] == slots[pack["kind"]],
                 "stable lock order/slot mismatch")
        _require(isinstance(pack.get("version"), list) and len(pack["version"]) == 3
                 and all(type(n) is int and n >= 0 for n in pack["version"]),
                 "invalid stable lock version")
        _require(isinstance(pack.get("name"), str) and pack["name"].strip(),
                 "stable lock pack name missing")
        _valid_tree_ref(pack)
        _require(isinstance(pack.get("modules"), list) and pack["modules"],
                 "stable lock modules missing")
        _require(isinstance(pack.get("dependencies"), list), "stable lock dependencies missing")
        source = pack.get("source")
        canonical_source = CANONICAL_SOURCE.fullmatch(source) if isinstance(source, str) else None
        valid_source = source == "observed-installed" or canonical_source
        if canonical_source:
            valid_source = canonical_source.group(1) not in (".", "..") and canonical_source.group(2) not in (".", "..")
        third_party = THIRD_PARTY_SOURCE.fullmatch(source) if isinstance(source, str) else None
        if third_party:
            try:
                parsed = datetime.fromisoformat(third_party.group(1).replace("Z", "+00:00"))
                valid_source = parsed.tzinfo is not None and parsed.utcoffset() is not None
            except ValueError:
                valid_source = False
        _require(bool(valid_source), "unsupported stable lock source")
    return packs


def _check_gate_b(receipt, lock_sha):
    _require(receipt.get("verdict") == "pass", "Gate B receipt verdict must be pass")
    _require(receipt.get("lock_file_sha256") == lock_sha,
             "Gate B receipt is bound to another stable lock")
    source_packs = receipt.get("candidate_source", {}).get("packs")
    _require(isinstance(source_packs, list), "Gate B candidate source packs missing")
    phases = receipt.get("phases", {})
    _require(phases.get("readback", {}).get("drift_zero") is True,
             "Gate B readback drifted")
    gametest = receipt.get("gametest", {})
    _require(gametest.get("status") == "pass", "Gate B GameTests did not pass")
    results = gametest.get("results")
    _require(isinstance(results, list) and len(results) == 6,
             "Gate B must contain six GameTest runs")
    ids, run_ids = set(), set()
    for row in results:
        _require(isinstance(row, dict) and row.get("verdict") == "pass",
                 "Gate B GameTest run failed")
        _require(row.get("phase") in ("first_start", "same_world_restart"),
                 "Gate B GameTest phase invalid")
        test_id, run_id = row.get("test"), row.get("run_id")
        _require(isinstance(test_id, str) and test_id and isinstance(run_id, str) and run_id,
                 "Gate B GameTest identity missing")
        ids.add(test_id)
        _require(run_id not in run_ids, "Gate B reused a GameTest run_id")
        run_ids.add(run_id)
        checks = row.get("checks")
        _require(isinstance(checks, dict) and checks and all(value is True for value in checks.values()),
                 "Gate B GameTest checks missing or false")
    _require(len(ids) == 3 and len(run_ids) == 6
             and all(sum(r.get("test") == test and r.get("phase") == phase for r in results) == 1
                     for test in ids for phase in ("first_start", "same_world_restart")),
             "Gate B must run three distinct tests once in each phase")
    fixture = gametest.get("fixture", {})
    _require(fixture.get("removed_after_readback") is True, "Gate B fixture was not removed")
    observers = gametest.get("observers")
    _require(isinstance(observers, list) and observers
             and all(isinstance(o, dict) and o.get("restored") is True for o in observers),
             "Gate B observers were not restored")
    _require(gametest.get("station_census", {}).get("comparison", {}).get(
        "same_station_ids_and_counts") is True, "Gate B station census changed")
    _require(phases.get("world_dynamic_properties", {}).get("comparison", {}).get(
        "same_keys_and_types") is True, "Gate B dynamic properties changed")
    changed = phases.get("original_players", {}).get("changed_original_records")
    _require(isinstance(changed, dict) and changed and all(v == [] for v in changed.values()),
             "Gate B original player records changed")
    gate = phases.get("perf_gate", {}).get("gate", {})
    _require(gate.get("ok") is True and gate.get("owned_slowdowns") == 0,
             "Gate B performance gate failed")
    windows = phases.get("windows", {})
    _require(isinstance(windows.get("first_seconds"), (int, float))
             and windows["first_seconds"] >= 120
             and isinstance(windows.get("restart_seconds"), (int, float))
             and windows["restart_seconds"] >= 30,
             "Gate B sampling windows are too short")
    prepare = phases.get("prepare", {})
    _require(prepare.get("mode") == "verified_lkg_restore"
             and prepare.get("status") == "restored_verified"
             and prepare.get("source_hashes_match") is True
             and prepare.get("target_hashes_match") is True,
             "Gate B did not use a verified LKG restore")
    backend = receipt.get("native_backend", {})
    _require(backend.get("backend") == "direct_native" and backend.get("live") is False,
             "Gate B must use isolated direct-native backend")
    admissions = backend.get("admissions")
    _require(isinstance(admissions, list) and admissions
             and all(isinstance(a, dict) and a.get("ok") is True
                     and isinstance(a.get("reserve_bytes"), int)
                     and a["reserve_bytes"] >= MIN_RESERVE_BYTES
                     and a.get("swap_limit_bytes") == 0 for a in admissions),
             "Gate B native backend admission failed")
    return source_packs


def _check_rollback_exercise(policy):
    receipt, _, _ = _regular_json(policy.get("stable_rollback_exercise"),
                                  "stable rollback exercise")
    _require(receipt.get("status") == "rehearsed"
             and receipt.get("rollback_exercise_complete") is True,
             "W2.5 rollback exercise is not complete")
    fault = receipt.get("fault", {})
    _require(fault.get("injected_module_error_confirmed") is True
             and fault.get("script_error_monitor_verified") is True,
             "W2.5 native module fault/monitor was not confirmed")
    _require(receipt.get("rollback_timing", {}).get("within_15_minutes") is True,
             "W2.5 rollback exceeded 15 minutes")
    restore = receipt.get("restore", {})
    _require(restore.get("world_and_global_hashes_match_backup") is True
             and restore.get("previous_lock_drift_zero") is True,
             "W2.5 rollback did not restore the backup and previous lock")


def validate(incoming, policy, policy_path, hashes):
    """Validate stable lock + Gate B references and bind them to family receipt."""
    lock, _, lock_sha = _regular_json(policy.get("stable_lock"), "stable lock")
    gate_b, _, _ = _regular_json(policy.get("stable_gate_b"), "Gate B receipt")
    _check_rollback_exercise(policy)
    lock_packs = _validate_lock(lock)
    source_packs = _check_gate_b(gate_b, lock_sha)
    approved_path = policy.get("approved_receipt")
    _require(isinstance(approved_path, str) and approved_path, "approved family receipt missing")
    approved = Path(approved_path)
    _require(approved.is_file() and not approved.is_symlink(), "approved receipt must be a regular file")
    approved_sha = hashlib.sha256(approved.read_bytes()).hexdigest()
    deferred = policy.get("deferred_client_acceptance", {})
    _require(deferred.get("source") == "explicit_user_instruction"
             and deferred.get("instruction") and deferred.get("recorded_at")
             and deferred.get("receipt_sha256") == approved_sha,
             "client deferral does not bind the exact approved receipt")
    family = json.loads(approved.read_bytes())
    acceptance = family.get("acceptance", {})
    _require(family.get("production_ready") is False and acceptance.get("client") is False
             and acceptance.get("static") is True and acceptance.get("bds") is True,
             "approved family receipt must pass static/BDS and keep client/production false")
    manifest = family.get("packs")
    _require(isinstance(manifest, list) and manifest, "approved family pack manifest missing")
    by_uid = {row.get("uuid"): row for row in manifest if isinstance(row, dict)}
    _require(len(by_uid) == len(manifest), "duplicate or invalid approved family UUID")
    _require(len(lock_packs) == len(manifest) == len(incoming),
             "incoming, stable lock, and approved family pack counts differ")
    by_incoming = {p.get("uuid"): p for p in incoming if isinstance(p, dict)}
    _require(len(by_incoming) == len(incoming), "duplicate or invalid incoming UUID")
    _require(set(by_uid) == set(by_incoming) == {p["uuid"] for p in lock_packs},
             "incoming UUID set differs from approved family and stable lock")
    order = family.get("order")
    _require(isinstance(order, dict), "approved family side order missing")
    for side in ("behavior", "resource"):
        expected_order = order.get(side)
        lock_order = [p["uuid"] for p in lock_packs if p["kind"] == side]
        _require(isinstance(expected_order, list)
                 and all(isinstance(uid, str) for uid in expected_order)
                 and len(expected_order) == len(set(expected_order)) and expected_order == lock_order,
                 "stable lock slot order differs from approved family " + side + " order")
    _require(len(source_packs) == len(lock_packs), "Gate B source pack count differs from stable lock")
    for lp, sp in zip(lock_packs, source_packs):
        _require(sp.get("path") == lp["path"] and sp.get("sha256") == lp["sha256"],
                 "Gate B candidate source differs from stable lock")
    for lp in lock_packs:
        uid = lp["uuid"]
        row, item = by_uid[uid], by_incoming[uid]
        _require(item.get("version") == row.get("version") == lp["version"],
                 "incoming version differs from approved family and stable lock: " + uid)
        _require(row.get("side") == lp["kind"],
                 "stable lock kind differs from approved family side: " + uid)
        _require(hashes(item["path"]) == row.get("files"),
                 "incoming pack file hashes differ from approved family: " + uid)
        _require(row.get("source", {}).get("owner") != "owned"
                 or (not row["source"].get("working_candidate") and row["source"].get("commit")),
                 "owned source must be committed: " + uid)
        manifest_path = Path(item["path"]) / "manifest.json"
        _require(manifest_path.is_file() and not manifest_path.is_symlink(),
                 "incoming manifest missing: " + uid)
        actual = json.loads(manifest_path.read_bytes())
        header = actual.get("header", {})
        _require(header.get("uuid") == uid and header.get("version") == lp["version"]
                 and header.get("name") == lp["name"]
                 and actual.get("modules") == lp["modules"]
                 and actual.get("dependencies", []) == lp["dependencies"]
                 and row.get("dependencies", []) == lp["dependencies"],
                 "incoming manifest differs from stable lock contract: " + uid)
