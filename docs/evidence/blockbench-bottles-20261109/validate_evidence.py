#!/usr/bin/env python3
"""Check saved evidence and rerun existing audits in a fresh extraction.

No GUI actions, scene generation, runtime edits, or changed surface calculations.
"""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import zipfile

from PIL import Image

HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def read(path):
    return json.loads(path.read_text())


def relative_file(root, name):
    """Resolve only canonical relative names within the declared input root."""
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError("Invalid relative evidence path")
    relative = PurePosixPath(name)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in name.split("/")):
        raise ValueError("Absolute, empty, dot or parent path components are not allowed")
    root = root.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError("Evidence path resolves outside its declared root")
    return path


def verify_inventory(root):
    root = root.resolve()
    inventory = read(relative_file(root, "artifact-sha256.json"))
    listed = set()
    for row in inventory["files"]:
        path = relative_file(root, row["file"])
        if path in listed:
            raise ValueError("Duplicate artifact inventory path")
        listed.add(path)
        assert path.stat().st_size == row["bytes"] and sha(path) == row["sha256"], row["file"]
    actual = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("Evidence payload must not contain symbolic links")
        if path.is_file():
            actual.add(relative_file(root, path.relative_to(root).as_posix()))
    excluded = {root / "artifact-sha256.json", root / "verification.json"}
    if listed & excluded or actual != listed | excluded:
        raise ValueError("Artifact inventory has missing, extra or excluded-file rows")


def output_location(path, repository=None):
    """Allow only new external outputs, never evidence or a Git checkout."""
    target = path.resolve()
    blocked = [HERE.resolve()]
    if repository:
        blocked.append(repository.resolve())
    if any(target == root or target.is_relative_to(root) for root in blocked):
        raise ValueError("Output must be outside the evidence and repository roots")
    # This also covers an omitted --repository, other worktrees and symlink aliases.
    markers = [parent / ".git" for parent in [target, *target.parents]]
    if any(marker.is_file() or (marker.is_dir() and (marker / "HEAD").is_file()) for marker in markers):
        raise ValueError("Output must be outside every Git checkout")
    if path.exists() or path.is_symlink() or target.exists() or target.is_symlink():
        raise FileExistsError("Output destination must not already exist")
    return target


def same_json_values_and_types(left, right):
    # Compare in memory only. Preserve array order, scalar types and exact numbers;
    # ignore only JSON object-key ordering. Never rewrite the saved evidence.
    options = {"sort_keys": True, "separators": (",", ":"), "allow_nan": False}
    return json.dumps(left, **options) == json.dumps(right, **options)


def verify(work, repository):
    verify_inventory(HERE)

    archives = read(HERE / "archive-entries.json")
    assert len(archives) == 7
    entries = {}
    archive_paths = set()
    for archive in archives:
        path = relative_file(HERE, archive["file"])
        if path in archive_paths:
            raise ValueError("Duplicate archive path")
        archive_paths.add(path)
        assert path.stat().st_size == archive["bytes"] < 200000
        assert sha(path) == archive["sha256"]
        with zipfile.ZipFile(path) as source:
            expected = {row["file"]: row for row in archive["entries"]}
            assert len(expected) == len(archive["entries"])
            for name in source.namelist():
                relative_file(work, name)
            assert set(source.namelist()) == set(expected)
            assert len(source.namelist()) == len(expected)
            assert source.testzip() is None
            for name, row in expected.items():
                relative = PurePosixPath(name)
                target = relative_file(work, name)
                assert relative.parts[0] == "review" and name not in entries
                raw = source.read(name)
                assert len(raw) == row["bytes"] and digest(raw) == row["sha256"], name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                entries[name] = row
    assert len(entries) == 673
    assert archive_paths == {path.resolve() for path in (HERE / "archives").glob("*.zip")}

    manifest = read(work / "review/bottles/manifest.json")
    review_root = work / "review"
    for name in manifest["inputs"]:
        relative_file(review_root, name)
    families = {row["name"]: row for row in manifest["families"]}
    assert len(families) == len(manifest["families"]) == 25
    for family in families.values():
        for field in ["scene", "bp"]:
            relative_file(review_root, family[field])
        for state in family["states"]:
            for field in ["java_model", "java_texture", "canonical_geometry", "canonical_texture"]:
                relative_file(review_root, state[field])
    scenes = {"review/" + row["scene"]: row["scene_sha256"] for row in families.values()}
    assert len(scenes) == 25
    for path, expected in scenes.items():
        assert sha(relative_file(work, path)) == expected

    progress = read(HERE / "gui-progress.json")
    assert progress["status"] == "complete_bounded_editor_review"
    assert not progress["pending_families"] and not progress["remaining_families"]
    assert progress["remaining_count_states"] == 0 and progress["completed_count_states"] == 97
    assert set(progress["completed_families"]) == set(families)
    images = progress["raw_gui_images"]
    assert len(images) == 75
    grouped = collections.defaultdict(list)
    dimensions = collections.Counter()
    for row in images:
        path = relative_file(HERE, row["file"])
        relative_file(work, row["scene"])
        assert row["actual_gui_captured_and_inspected"] is True
        assert sha(path) == row["sha256"]
        assert row["scene"] in scenes and row["scene_sha256"] == scenes[row["scene"]]
        family = families[row["family"]]
        assert row["counts"] == [state["count"] for state in family["states"]]
        with Image.open(path) as image:
            assert image.format == "JPEG"
            dimensions["%sx%s" % image.size] += 1
            image.verify()
        target = relative_file(work, row["file"])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        assert sha(target) == row["sha256"]
        grouped[row["family"]].append(row)
    assert set(grouped) == set(families)
    for rows in grouped.values():
        assert len(rows) == 3 and {row["view"] for row in rows} == {"perspective", "top", "bottom"}
        assert len({row["sha256"] for row in rows}) == 3
    assert sum(len(rows[0]["counts"]) for rows in grouped.values()) == 97
    assert dict(dimensions) == {"1364x1024": 23, "1188x848": 52}
    accepted = {row["file"] for row in images}
    actual = {path.relative_to(HERE).as_posix() for path in (HERE / "review/bottles/evidence").glob("*.jpg")}
    assert accepted == actual
    provenance = read(HERE / "capture-provenance.json")
    assert sha(HERE / "gui-progress.json") == provenance["portable_record_sha256"]
    assert read(HERE / "gui-progress-completion-correction.json")["after_sha256"] == provenance["source_record_sha256"]
    for row in provenance["excluded_diagnostics"]:
        assert not relative_file(HERE / "review/bottles/evidence", row["original_basename"]).exists()

    baseline = read(HERE / "baseline-input-verification.json")
    runtime_inputs = {path.removeprefix("inputs/source/"): row["sha256"] for path, row in manifest["inputs"].items() if path.startswith("inputs/source/runtime/")}
    assert len(runtime_inputs) == 148 == baseline["checked_input_count"]
    assert len(baseline["inputs"]) == len({row["path"] for row in baseline["inputs"]}) == 148
    assert {row["path"]: row["review_sha256"] for row in baseline["inputs"]} == runtime_inputs
    for row in baseline["inputs"]:
        relative_file(review_root / "inputs/source", row["path"])
        assert row["equal"] and row["base_sha256"] == row["review_sha256"]
    if repository:
        for path, expected in runtime_inputs.items():
            assert sha(relative_file(repository, path)) == expected, path

    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONOPTIMIZE="0")
    env.pop("TAVERN_AUDIT_OUTPUT", None)
    checks = []
    for script, report in [
        ("validate_scenes.py", "static-checks.json"),
        ("check_routing.py", "routing.json"),
        ("compare_faces.py", "face-uv-diagnostic.json"),
        ("verify_face_adaptations.py", "face-adaptation-verification.json"),
    ]:
        result = subprocess.run([sys.executable, str(work / "review/bottles" / script)], cwd=work, env=env, capture_output=True, text=True)
        assert result.returncode == 0, script + ": " + result.stderr.replace(str(work), ".")
        saved = work / "review/bottles" / report
        generated = work / "review/rerun/bottles" / report
        assert same_json_values_and_types(read(generated), read(saved)), report
        byte_equal = generated.read_bytes() == saved.read_bytes()
        checks.append({"audit": script, "report": report, "json_values_and_types_identical_saved_report": True, "byte_identical_saved_report": byte_equal, "saved_sha256": sha(saved), "rerun_sha256": sha(generated), "serialization_note": "Identical bytes." if byte_equal else "Only JSON object-key order differs. The unchanged routing audit iterates filesystem glob order; complete parsed JSON values, types and array order are exactly equal."})

    method = HERE / "analyze_surfaces.py"
    portability = read(HERE / "surface-portability-validation.json")
    assert sha(method) == portability["portable_method_sha256"]
    shutil.copyfile(method, work / method.name)
    result = subprocess.run([sys.executable, str(work / method.name)], cwd=work, env=env, capture_output=True, text=True)
    assert result.returncode == 0, "Surface analysis: " + result.stderr.replace(str(work), ".")
    assert (work / "rerun/surface-analysis.json").read_bytes() == (HERE / "surface-analysis.json").read_bytes()
    surface = read(HERE / "surface-analysis.json")
    assert len(surface["state_views"]) == 30
    assert sum(row["covered_union_rays"] for row in surface["state_views"]) == 111188
    assert surface["madame_count1_top_exact_rgb_proof"]["exactly_equal"]
    assert len(surface["additional_exact_rgb_proofs"]) == 2
    assert all(row["exactly_equal"] for row in surface["additional_exact_rgb_proofs"])
    for path, expected in scenes.items():
        assert sha(relative_file(work, path)) == expected

    return {
        "passed": True,
        "archive_count": 7,
        "archive_entries_verified": 673,
        "all_archives_under_200000_bytes": True,
        "scene_files_unchanged": 25,
        "count_states": 97,
        "accepted_raw_jpegs": 75,
        "capture_dimensions": dict(dimensions),
        "each_family_three_views_and_distinct_hashes": True,
        "invalid_and_white_diagnostics_excluded": 3,
        "base_commit": baseline["base_commit"],
        "base_runtime_git_tree": baseline["base_runtime_git_tree"],
        "base_runtime_inputs_recorded_equal": 148,
        "current_repository_runtime_inputs_rechecked": 148 if repository else 0,
        "numerical_audits": checks,
        "surface_analysis_byte_identical_saved_report": True,
        "surface_analysis_sha256": sha(HERE / "surface-analysis.json"),
        "surface_state_views": 30,
        "surface_covered_rays": 111188,
        "exact_original_rgb_crop_proofs": 3,
        "surface_algorithm_changed": False,
        "gui_opened_by_verifier": False,
        "engine_acceptance": False,
        "scene_rebuilt": False,
        "runtime_changed": False,
    }


def main():
    if not __debug__:
        raise RuntimeError("Run without Python optimization; verification requires assertions")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, help="Optional canonical checkout for rechecking the 148 runtime input hashes.")
    parser.add_argument("--work-dir", type=Path, help="New external directory in which to retain the independent extraction; outside evidence and Git checkouts.")
    parser.add_argument("--report", type=Path, help="New external summary file; outside evidence and Git checkouts. Existing files are never overwritten.")
    args = parser.parse_args()
    repository = args.repository.resolve() if args.repository else None
    report = output_location(args.report, repository) if args.report else None
    if args.work_dir:
        work = output_location(args.work_dir, repository)
        work.mkdir(parents=True, exist_ok=False)
        result = verify(work, repository)
    else:
        with tempfile.TemporaryDirectory(prefix="tavern-bottle-evidence-") as tmp:
            result = verify(Path(tmp), repository)
    if report:
        # Recheck after the audits, then use exclusive creation to prevent overwrite.
        report = output_location(report, repository)
        report.parent.mkdir(parents=True, exist_ok=True)
        with report.open("x") as stream:
            stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
