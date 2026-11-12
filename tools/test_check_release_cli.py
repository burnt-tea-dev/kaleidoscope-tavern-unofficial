#!/usr/bin/env python3
"""Keep optional pinned source validation intact in the aggregate release CLI."""
from pathlib import Path
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from PIL import Image
from animated_item_render_contract import planned as animated_outputs
from build_potion_bottle_visual import MODEL, TEXTURE, outputs as potion_outputs

from check_release import ROOT, ANIMATED_ITEM_GEOMETRIES, REVIEWED_VISUAL_GEOMETRIES, REVIEWED_VISUAL_SOURCE, REVIEWED_VISUAL_RELEASE, check_combined_geometry_budget, parse_args, source_check_commands


class ReleaseSourceArguments(unittest.TestCase):
    def test_default_still_runs_both_source_checks_without_optional_pins(self):
        commands = source_check_commands(parse_args([]), "0.6.89")
        self.assertEqual(commands, {
            "storage": [sys.executable, str(ROOT / "tools/check_storage_rendering.py")],
            "launch": [sys.executable, str(ROOT / "tools/check_launch.py")],
        })

    def test_pinned_java_reaches_both_checks_and_writes_storage_evidence(self):
        java = Path("source fixtures/java checkout")
        commands = source_check_commands(parse_args(["--java-source", str(java)]), "0.6.89")
        for command in commands.values():
            self.assertEqual(command[command.index("--java-source") + 1], str(java.resolve()))
        report = commands["storage"][commands["storage"].index("--report") + 1]
        self.assertEqual(report, str(ROOT / "docs/STORAGE-VALIDATION-0.6.89.json"))
        self.assertNotIn("--report", commands["launch"])

    def test_baseline_reaches_launch_check_without_requiring_java(self):
        baseline = Path("source fixtures/pinned baseline")
        commands = source_check_commands(parse_args(["--baseline", str(baseline)]), "0.6.89")
        self.assertEqual(commands["launch"][-2:], ["--baseline", str(baseline.resolve())])
        self.assertNotIn("--baseline", commands["storage"])
        self.assertNotIn("--java-source", commands["launch"])

    def test_combined_pins_are_separate_arguments_not_shell_text(self):
        args = parse_args(["--java-source", "java $source", "--baseline", "base; source"])
        commands = source_check_commands(args, "0.6.89")
        launch = commands["launch"]
        self.assertEqual(launch.count("--java-source"), 1)
        self.assertEqual(launch.count("--baseline"), 1)
        self.assertEqual(launch[-1], str(Path("base; source").resolve()))

    def test_cli_help_exposes_pins_before_running_validators(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools/check_release.py"), "--help"],
                                check=True, capture_output=True, text=True)
        self.assertIn("--java-source", result.stdout)
        self.assertIn("--baseline", result.stdout)


class GeometryBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        reference=json.loads((ROOT/'art/interfaces/animated-item-java-reference.json').read_text())
        allocation_files={str(path.relative_to(ROOT)) for path in animated_outputs()}|set(REVIEWED_VISUAL_GEOMETRIES.values())
        allocation_files|={source['texture'] for source in reference['sources'].values()}|{'art/interfaces/item-art-map.json'}
        for name in allocation_files:
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes((ROOT/name).read_bytes())
        witnesses={name:{'before':None,'after':hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),
                         'release':REVIEWED_VISUAL_RELEASE,'reviewedSourceCommit':REVIEWED_VISUAL_SOURCE} for name in REVIEWED_VISUAL_GEOMETRIES.values()}
        for name,value in {
            'data/baseline-reconciliation.json':{'schema':1,'testOnly':True,'files':witnesses},
            'art/interfaces/animated-item-java-reference.json':reference,
        }.items():
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value))
        self.inventory={f'geometry.original_{i}':[self.root/f'original_{i}.json'] for i in range(1023)}
        self.inventory.update({identifier:[self.root/name] for identifier,name in ANIMATED_ITEM_GEOMETRIES.items()})
        self.inventory.update({identifier:[self.root/name] for identifier,name in REVIEWED_VISUAL_GEOMETRIES.items()})
        self.potion_ids={}
        for name in set(potion_outputs())|{MODEL,TEXTURE,str(Path(TEXTURE).with_suffix('.texture_set.json'))}:
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes((ROOT/name).read_bytes())
        for name,value in potion_outputs().items():
            if isinstance(value,dict):
                for geometry in value.get('minecraft:geometry',[]):
                    self.potion_ids[geometry['description']['identifier']]=self.root/name
        self.inventory.update({identifier:[path] for identifier,path in self.potion_ids.items()})

    def test_exact_source_allocations_preserve_the_original_base_ceiling(self):
        result=check_combined_geometry_budget(self.inventory,self.root)
        self.assertEqual((result['geometries'],result['base_geometries']),(1348,1023))
        self.assertEqual(result['animated_item_contract_geometries'],5)
        self.assertEqual(result['animated_item_max_allocated_vertices'],1200)
        self.assertEqual(result['base_limit_exclusive'],1024)
        for allocation in result['animated_item_allocations'].values():
            self.assertEqual((allocation['ids'],allocation['max_bones'],allocation['display_contexts']),(1,1,8))
            self.assertLessEqual(allocation['max_allocated_vertices'],1200)
        self.assertEqual(result['reviewed_visual_geometries'],316)
        self.assertEqual(result['visual_allocations']['runtime/RP/models/entity/board_glyph_outline.geo.json']['max_allocated_vertices'],384)
        self.assertEqual(result['visual_allocations']['runtime/RP/models/entity/signature_rgb_texels.geo.json']['max_allocated_vertices'],672)
        self.assertEqual(result['potion_contract_geometries'],4)
        self.assertEqual(result['potion_allocations']['runtime/RP/models/entity/potion_liquid_texels.geo.json']['max_allocated_vertices'],504)
        self.inventory['geometry.unreviewed_sixth']=[self.root/'sixth.geo.json']
        with self.assertRaisesRegex(AssertionError,'base geometry budget exceeded'):
            check_combined_geometry_budget(self.inventory,self.root)

    def test_same_total_cannot_replace_a_reviewed_id_with_an_arbitrary_model(self):
        self.inventory.pop(next(iter(ANIMATED_ITEM_GEOMETRIES)))
        self.inventory['geometry.unreviewed_replacement']=[self.root/'replacement.geo.json']
        self.assertEqual(len(self.inventory),1348)
        with self.assertRaisesRegex(AssertionError,'one exact Tavern owner/path'):
            check_combined_geometry_budget(self.inventory,self.root)

    def test_duplicate_or_moved_claim_cannot_hide_behind_the_identifier_set(self):
        for identifier in ANIMATED_ITEM_GEOMETRIES:
            original=self.inventory[identifier]
            for paths in [original+[self.root/'peer/duplicate.geo.json'],[self.root/'unscanned/moved.geo.json']]:
                self.inventory[identifier]=paths
                with self.assertRaisesRegex(AssertionError,'one exact Tavern owner/path'):
                    check_combined_geometry_budget(self.inventory,self.root)
            self.inventory[identifier]=original

    def test_same_identifier_does_not_allow_changed_mesh_or_display(self):
        path=self.root/'runtime/RP/models/entity/item_sprite_tartaric_acid_painting.geo.json'
        original=json.loads(path.read_text())
        for mutate in [
            lambda models:models.append(copy.deepcopy(models[0])),
            lambda models:models[0]['bones'][0]['cubes'].append(copy.deepcopy(models[0]['bones'][0]['cubes'][0])),
            lambda models:models[0]['bones'][0]['cubes'][1]['origin'].__setitem__(0,99),
            lambda models:models[0]['item_display_transforms'].pop('firstperson_lefthand'),
            lambda models:models[0]['item_display_transforms']['gui'].update(scale=[9,9,9]),
        ]:
            value=copy.deepcopy(original);mutate(value['minecraft:geometry']);path.write_text(json.dumps(value))
            with self.assertRaisesRegex(AssertionError,'Animated item render route drift'):
                check_combined_geometry_budget(self.inventory,self.root)

    def test_source_set_and_pixels_cannot_be_removed_or_replaced(self):
        path=self.root/'art/interfaces/animated-item-java-reference.json';original=json.loads(path.read_text())
        for name in original['sources']:
            value=copy.deepcopy(original);del value['sources'][name];path.write_text(json.dumps(value))
            with self.assertRaisesRegex(AssertionError,'Incomplete animated item source contract'):
                check_combined_geometry_budget(self.inventory,self.root)
        value=copy.deepcopy(original);value['sources']['unowned']=copy.deepcopy(next(iter(value['sources'].values())))
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(AssertionError,'Incomplete animated item source contract'):
            check_combined_geometry_budget(self.inventory,self.root)
        value=copy.deepcopy(original);value['sources']['tartaric_acid_painting']['rgba_sha256']='0'*64;path.write_text(json.dumps(value))
        with self.assertRaisesRegex(AssertionError,'source pixels changed'):
            check_combined_geometry_budget(self.inventory,self.root)

    def test_unowned_animated_prefix_stays_in_base_and_1024_is_rejected(self):
        self.inventory.pop('geometry.original_0')
        self.inventory['geometry.kt_runtime.item_sprite_unowned']=[self.root/'unowned.geo.json']
        self.assertEqual(check_combined_geometry_budget(self.inventory,self.root)['base_geometries'],1023)
        self.inventory['geometry.extra_unowned']=[self.root/'extra.geo.json']
        with self.assertRaisesRegex(AssertionError,'base geometry budget exceeded.*1024'):
            check_combined_geometry_budget(self.inventory,self.root)

    def test_source_backed_mesh_still_cannot_exceed_allocated_vertex_ceiling(self):
        reference_path=self.root/'art/interfaces/animated-item-java-reference.json'
        reference=json.loads(reference_path.read_text());source=reference['sources']['tartaric_acid_painting']
        # A genuine generated alpha shell can require 65 cubes. Even with
        # coherent source pixels/counts, it must not enlarge this allocation.
        sheet=Image.new('RGBA',source['size'])
        for y in range(sheet.height):
            for x in range(sheet.width):
                if (x+y)%2:sheet.putpixel((x,y),(255,255,255,255))
        sheet.save(self.root/source['texture']);source['rgba_sha256']=hashlib.sha256(sheet.tobytes()).hexdigest()
        reference_path.write_text(json.dumps(reference))
        for path,value in animated_outputs(self.root).items():path.write_text(json.dumps(value))
        with self.assertRaisesRegex(AssertionError,'Animated item source mesh budget exceeded'):
            check_combined_geometry_budget(self.inventory,self.root)

    def test_visual_allocation_rejects_missing_duplicate_or_moved_mesh(self):
        identifier=next(iter(REVIEWED_VISUAL_GEOMETRIES));original=self.inventory[identifier]
        for paths in [[],original+[self.root/'peer/duplicate.geo.json'],[self.root/'moved.geo.json']]:
            self.inventory[identifier]=paths
            with self.assertRaisesRegex(AssertionError,'one exact Tavern owner/path'):
                check_combined_geometry_budget(self.inventory,self.root)

    def test_visual_allocation_rejects_unreviewed_source_and_extra_cubes(self):
        name=next(iter(REVIEWED_VISUAL_GEOMETRIES.values()));path=self.root/name
        ledger_path=self.root/'data/baseline-reconciliation.json';ledger=json.loads(ledger_path.read_text())
        ledger['files'][name]['reviewedSourceCommit']='0'*40;ledger_path.write_text(json.dumps(ledger))
        with self.assertRaisesRegex(AssertionError,'Visual geometry allocation source changed'):
            check_combined_geometry_budget(self.inventory,self.root)
        ledger['files'][name]['reviewedSourceCommit']=REVIEWED_VISUAL_SOURCE;ledger_path.write_text(json.dumps(ledger))
        geometry=json.loads(path.read_text());bones=geometry['minecraft:geometry'][0]['bones'];cube=next(b['cubes'][0] for b in bones if b.get('cubes'))
        bones[-1].setdefault('cubes',[]).append(copy.deepcopy(cube));path.write_text(json.dumps(geometry))
        with self.assertRaisesRegex(AssertionError,'Reviewed visual geometry changed'):
            check_combined_geometry_budget(self.inventory,self.root)
        # Even an updated digest cannot enlarge the source-reviewed allocation.
        ledger['files'][name]['after']=hashlib.sha256(path.read_bytes()).hexdigest();ledger_path.write_text(json.dumps(ledger))
        with self.assertRaisesRegex(AssertionError,'Visual allocation cube budget exceeded'):
            check_combined_geometry_budget(self.inventory,self.root)

    def test_potion_contract_rejects_missing_duplicate_or_moved_owner(self):
        identifier,path=next(iter(self.potion_ids.items()))
        for paths in [[],[path,self.root/'peer/duplicate.geo.json'],[self.root/'moved.geo.json']]:
            self.inventory[identifier]=paths
            with self.assertRaisesRegex(AssertionError,'Potion geometry must have one exact Tavern owner/path'):
                check_combined_geometry_budget(self.inventory,self.root)

    def test_potion_accounting_cannot_hide_changed_mesh_or_broken_wiring(self):
        for name,mutate in [
            ('runtime/RP/models/entity/potion_liquid_texels.geo.json',
             lambda value:value['minecraft:geometry'][0]['bones'][0]['cubes'].append(copy.deepcopy(value['minecraft:geometry'][0]['bones'][0]['cubes'][0]))),
            ('runtime/RP/entity/potion_liquid_visual.entity.json',
             lambda value:value['minecraft:client_entity']['description'].update(render_controllers=[])),
        ]:
            path=self.root/name;original=path.read_bytes();value=json.loads(original);mutate(value)
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(AssertionError,'Stale generated potion resource'):
                check_combined_geometry_budget(self.inventory,self.root)
            path.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
