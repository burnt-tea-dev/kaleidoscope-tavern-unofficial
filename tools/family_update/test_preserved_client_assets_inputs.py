"""Fixed client-asset source admission and fresh-save boundaries, all synthetic."""
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import sys
from contextlib import ExitStack
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from family_update import common as c, deploy_live, prospective_preserved_inputs as dispatch
from family_update import preserved_client_assets_inputs as m
from family_guard import hashes, atomic


class ClientInputBoundaries(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.ext, self.run, self.live = [self.root / name for name in ['source', 'run', 'live']]
        self.head, self.tree = 'a' * 40, 'b' * 40
        self.write(self.ext / 'baseline.json', {'repository': m.PRIVATE, 'version': m.VERSION})
        sets = [f'textures/items/kfv_item_{n:03}.texture_set.json' for n in range(156)]
        normals = [f'textures/items/kfv_item_{n:03}_normal.png' for n in range(156)]
        self.recipe = {'schema': 1, 'profile': m.PROFILE, 'source_package_version': m.VERSION,
            'uuids': {}, 'before_versions': {}, 'versions': {}, 'input_hashes': {}, 'output_hashes': {}, 'changed': {},
            'source_facts': {'legacy_identifiers': [f'amw:retired_{n:02}' for n in range(31)],
                             'item_heightmap_sets': sets, 'normal_files': normals},
            'patch_source_sha256': {'tools/client_assets.py': 'c' * 64},
            'client': False, 'native_loading': False, 'production_ready': False}
        paths = m.patch_paths(self.recipe)
        self.preserved, self.candidate, self.outputs, self.priors, self.manifests = [], [], {}, {}, {}
        for name, (uid, side, before, after) in m.PACKS.items():
            peer = next(row[0] for key, row in m.PACKS.items() if key.split('_')[0] == name.split('_')[0] and key != name)
            prior = {'format_version': 2, 'header': {'uuid': uid, 'name': name, 'version': before, 'description': 'preserved'},
                'modules': [{'uuid': name + '-data', 'type': 'resources' if side == 'resource' else 'data', 'version': before}],
                'dependencies': [{'uuid': peer, 'version': before}]}
            if side == 'behavior':
                prior['modules'].append({'uuid': name + '-script', 'type': 'script', 'language': 'javascript', 'entry': 'scripts/main.js', 'version': [0, 0, 1]})
                prior['dependencies'].append({'module_name': '@minecraft/server', 'version': '2.1.0'})
            output = copy.deepcopy(prior)
            output['header'].update(name=prior['header']['name'] + ' [本機顯示修復 1.0.58]', version=after)
            for row in output['modules']: row['version'] = after
            output['dependencies'][0]['version'] = after
            old_root, new_root = self.live / name, self.root / 'prepared' / name
            self.write(old_root / 'manifest.json', prior)
            self.write(new_root / 'manifest.json', output)
            additions = {m.HELPER} if name == 'Fishing_BP' else set(normals) if name == 'Fishing_RP' else set()
            for p in paths[name] - {'manifest.json'}:
                if p not in additions: self.write(old_root / p, 'synthetic original ' + p)
                self.write(new_root / p, 'synthetic repaired ' + p)
            for folder in [old_root, new_root]: self.write(folder / 'assets/retained', 'unchanged synthetic asset')
            old_files, new_files = hashes(old_root), hashes(new_root)
            self.preserved.append({'uuid': uid, 'side': side, 'version': before, 'path': str(old_root), 'files': old_files, 'source': {'owner': 'preserved'}})
            self.candidate.append({'uuid': uid, 'side': side, 'version': after, 'files': new_files, 'source': {'owner': 'preserved'}})
            self.outputs[name] = {'uuid': uid, 'path': str(new_root)}
            self.priors[name], self.manifests[name] = prior, output
            self.recipe['uuids'][name], self.recipe['before_versions'][name], self.recipe['versions'][name] = uid, before, after
            self.recipe['input_hashes'][name], self.recipe['output_hashes'][name] = old_files, new_files
            self.recipe['changed'][name] = {p: {'before': old_files.get(p), 'after': new_files[p]} for p in paths[name]}
        other = self.live / 'other';self.write(other / 'asset', 'unaffected preserved bytes')
        row = {'uuid': 'other', 'side': 'resource', 'version': [1, 0, 0], 'path': str(other), 'files': hashes(other), 'source': {'owner': 'preserved'}}
        self.preserved.append(row);self.candidate.append(copy.deepcopy(row))
        self.original = {'packs': copy.deepcopy(self.preserved)}
        self.receipt = {'packs': self.candidate}
        self.admitted = self.root / 'admitted.json';self.write(self.admitted, self.original)
        self.recipe['approved_input_receipt_sha256'] = c.sha(self.admitted)
        self.write(self.run / 'production-before/senluo-policy.json', {'approved_receipt': str(self.admitted)})
        self.recipe_path = self.ext / m.RECIPE;self.write(self.recipe_path, self.recipe)
        self.log = self.root / 'ci/source.log';self.write(self.log, 'Synthetic test only; no client/native claim.')
        self.report_path = self.root / 'ci' / m.REPORT;self.write(self.report_path, {'test_log': {'name': self.log.name, 'sha256': c.sha(self.log)}})
        self.proof = self.root / 'proof.json';self.write(self.proof, {'differential': c.report_ref(self.report_path)})
        self.review = {'schema': 1, 'profile': m.PROFILE, 'source_commit': self.head,
            'recipe': {'path': m.RECIPE, 'sha256': c.sha(self.recipe_path)}, 'source_validation': c.report_ref(self.proof), 'packs': self.outputs}
        self.review_path = self.root / 'review.json';self.write(self.review_path, self.review)
        self.write(self.run / 'release-candidate/family-receipt.json', self.receipt)

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False) + '\n' if isinstance(value, dict) else value)

    def context(self):
        stack = ExitStack()
        stack.enter_context(patch.multiple(c, CONFIG={'prospective_preserved_inputs': str(self.review_path)}, EXTENSION=self.ext,
            R=self.run, C=self.run / 'release-candidate', B=self.live, W=self.live / 'world', Q=self.live / 'quality', SOURCES={'tavern': self.root / 'public'}))
        stack.enter_context(patch.multiple(deploy_live, CONFIG=c.CONFIG, R=c.R, C=c.C))
        stack.enter_context(patch.dict(c.G, {'hashes': hashes, 'atomic': atomic}))
        stack.enter_context(patch.object(c, 'git', side_effect=lambda root, *args: '' if args == ('status', '--porcelain') else self.tree if args[-1].endswith('^{tree}') else self.head))
        stack.enter_context(patch.object(dispatch, 'committed', side_effect=lambda path, _: self.assertTrue(path.is_file())))
        stack.enter_context(patch.object(m, 'APPROVED', c.sha(self.admitted)))
        stack.enter_context(patch.object(m, 'source_evidence', return_value=(c.report_ref(self.report_path), {'actual_current_source_commit': self.head, 'current_source_tree_oid': self.tree}, {'private_pull_request': 58})))
        return stack

    def select(self):
        with self.context(): return dispatch.select(self.preserved, self.original)

    def save_recipe(self):
        self.write(self.recipe_path, self.recipe)
        self.review['recipe']['sha256'] = c.sha(self.recipe_path);self.write(self.review_path, self.review)

    def test_four_outputs_preserve_other_pack_and_bind_source_inputs(self):
        original = copy.deepcopy(self.original)
        roots, selected = self.select()
        self.assertEqual(roots[-1], Path(self.preserved[-1]['path']))
        self.assertEqual(len(selected['packs']), 4)
        self.assertEqual(self.original, original)
        self.assertFalse(selected['current_live_reconciled'])
        with self.context():
            dispatch.verify_candidate(self.receipt, selected)
            refs = dispatch.input_refs()
        self.assertIn('prospective_client_assets_log', refs)
        self.assertNotIn('prospective_native_validation', refs)
        altered = copy.deepcopy(self.receipt);altered['packs'][-1]['files']['asset'] = 'f' * 64
        with self.context(), self.assertRaisesRegex(AssertionError, 'Unaffected candidate'):
            dispatch.verify_candidate(altered, selected)

    def test_all_captured_and_current_preserved_drift_fails(self):
        for scope in ['target', 'other', 'capture']:
            with self.subTest(scope=scope):
                rows = copy.deepcopy(self.preserved);original = copy.deepcopy(self.original)
                if scope == 'target':self.preserved[0]['files']['assets/retained'] = 'f' * 64
                elif scope == 'other':self.preserved[-1]['files']['asset'] = 'f' * 64
                else:self.original['packs'][-1]['files']['asset'] = 'f' * 64
                with self.assertRaises(AssertionError): self.select()
                self.preserved,self.original=rows,original

    def test_missing_pair_extra_file_and_deleted_core_tombstone_fail(self):
        removed=self.review['packs'].pop('AMW_BP');self.write(self.review_path, self.review)
        with self.assertRaises(AssertionError):self.select()
        self.review['packs']['AMW_BP']=removed;self.write(self.review_path, self.review)
        for name in ['AMW_BP', 'Fishing_RP']:
            original=copy.deepcopy(self.recipe)
            self.recipe['output_hashes'][name]['assets/unreviewed']='e'*64
            self.recipe['changed'][name]['assets/unreviewed']={'before':None,'after':'e'*64};self.save_recipe()
            with self.assertRaisesRegex(AssertionError, 'fixed repair'):self.select()
            self.recipe=original;self.save_recipe()
        self.recipe['output_hashes']['AMW_BP'].pop('assets/retained');self.save_recipe()
        with self.assertRaisesRegex(AssertionError, 'inventory removed'):self.select()

    def test_normals_must_be_exactly156_new_images_for_existing_sets(self):
        for field in ['item_heightmap_sets','normal_files']:
            old=copy.deepcopy(self.recipe['source_facts'])
            self.recipe['source_facts'][field].pop();self.save_recipe()
            with self.assertRaises(AssertionError):self.select()
            self.recipe['source_facts']=old;self.save_recipe()
        self.recipe['source_facts']['normal_files'][0]='textures/items/unreviewed.png';self.save_recipe()
        with self.assertRaises(AssertionError):self.select()

    def test_uuid_api_modules_metadata_and_peer_versions_stay_exact(self):
        prior,output=self.priors['Fishing_BP'],self.manifests['Fishing_BP']
        m.validate_manifest('Fishing_BP',output,prior)
        for mutate in [lambda d:d['modules'][0].update(uuid='replacement'),lambda d:d['modules'][1].update(version=[0,0,1]),
                       lambda d:d['dependencies'][1].update(version='2.9.0'),lambda d:d['dependencies'][0].update(version=[1,2,0]),
                       lambda d:d['header'].update(description='replaced'),lambda d:d['header'].update(name='author latest')]:
            wrong=copy.deepcopy(output);mutate(wrong)
            with self.assertRaises(AssertionError):m.validate_manifest('Fishing_BP',wrong,prior)

    def test_outputs_cannot_overlap_live_or_share_links(self):
        old=self.review['packs']['AMW_BP']['path'];self.review['packs']['AMW_BP']['path']=self.preserved[0]['path'];self.write(self.review_path,self.review)
        with self.assertRaisesRegex(AssertionError,'overlaps'):self.select()
        self.review['packs']['AMW_BP']['path']=old;self.write(self.review_path,self.review)
        Path(old,'linked').symlink_to(Path(old,'assets/retained'))
        with self.assertRaisesRegex(AssertionError,'symlink'):self.select()
        Path(old,'linked').unlink()
        os.link(Path(old,'assets/retained'),self.root/'shared-link')
        with self.assertRaisesRegex(AssertionError,'physical files'):self.select()

    def native(self):
        return {'fresh_stopped_backup':True,'existing_world_loaded':True,'exact_files_checked':True,'bds':True,'saved_world_migration':True,
            'candidate_receipt_sha256':c.sha(self.run/'release-candidate/family-receipt.json'),'client':False,'simulated_players':False,'test_only_overlays':[],
            'runs':[{'phase':phase,'ok':True,'errors':[],'real_player_connections':0,'player_records_unchanged':True,
                     'custom_container_inventories_retained':True,'native_freezer_inputs_retained':True} for phase in ['first','restart']]}

    def test_source_only_cannot_install_then_exact_fresh_first_restart_can(self):
        _,selected=self.select();self.write(self.run/'prospective-preserved-inputs-check.json',selected)
        with self.context(),self.assertRaises(FileNotFoundError):deploy_live.installation_selection(self.receipt,self.original)
        evidence=self.native();self.write(self.run/'saved-world-report.json',evidence)
        with self.context():
            m.bind_native(self.receipt,evidence)
            family,unchanged=deploy_live.installation_selection(self.receipt,self.original)
        self.assertEqual(len(family),4);self.assertEqual(len(unchanged),1)
        for field in ['fresh_stopped_backup','existing_world_loaded','exact_files_checked']:
            wrong=copy.deepcopy(evidence);wrong[field]=False
            with self.context(),self.assertRaises(AssertionError):m.bind_native(self.receipt,wrong)
        wrong=copy.deepcopy(evidence);wrong['runs'][1]['errors']=['native failure']
        with self.context(),self.assertRaises(AssertionError):m.bind_native(self.receipt,wrong)
        self.write(self.run/'saved-world-report.json',{'different':'save'})
        with self.context(),self.assertRaises(AssertionError):deploy_live.installation_selection(self.receipt,self.original)


if __name__=='__main__':unittest.main()
