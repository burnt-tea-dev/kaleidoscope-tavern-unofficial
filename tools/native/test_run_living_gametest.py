"""Declare native Player fixtures without accepting physical player connections."""
import json
from pathlib import Path
import tempfile
import unittest
import run_living_effects as runner


class NativePlayerBoundary(unittest.TestCase):
    def test_player_proposal_retains_native_fields_and_refuses_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'behavior_packs/vanilla/entities/player.json'
            source.parent.mkdir(parents=True)
            native = {'format_version': '1.26.30', 'minecraft:entity': {
                'description': {'identifier': 'minecraft:player'},
                'components': {'minecraft:collision_box': {'width': .6, 'height': 1.8}},
                'component_groups': {'native:group': {}}, 'events': {'native:event': {}}}}
            source.write_text(json.dumps(native))
            proposal = root/'proposal.json'
            delta = {'component_groups': {'qa:group': {}}, 'events': {'qa:on': {'add': {'component_groups': ['qa:group']}}}}
            proposal.write_text(json.dumps({'selected_sources': [{'file': 'vanilla/entities/player.json'}], 'qa_only_increment': delta}))
            raw, evidence = runner.player_component_proposal(root, proposal)
            result = json.loads(raw)
            for section, additions in delta.items():
                for name, value in additions.items():
                    self.assertEqual(result['minecraft:entity'][section].pop(name), value)
            self.assertEqual(result, native)
            self.assertEqual(json.loads(source.read_bytes()), native)
            self.assertEqual(evidence['source'], 'vanilla/entities/player.json')
            delta['events']['native:event'] = {}
            proposal.write_text(json.dumps({'selected_sources': [{'file': 'vanilla/entities/player.json'}], 'qa_only_increment': delta}))
            with self.assertRaisesRegex(AssertionError, 'replaces existing Player'):
                runner.player_component_proposal(root, proposal)

    def log(self, prefix='', players=0):
        # Completion fields need not be adjacent; the observer includes measurements.
        row = {'kind': 'done', 'observationOnly': True, 'phase': 'first', 'players': players}
        return prefix+'\n[LIVING_EFFECT_QA] '+json.dumps(row)+'\nQuit correctly\n'

    def test_overlay_preserves_canonical_manifest_and_existing_dependencies(self):
        raw = (runner.ROOT/'runtime/BP/manifest.json').read_bytes()
        original = json.loads(raw)
        overlay = json.loads(runner.gametest_manifest(raw))
        dependency = overlay['dependencies'].pop()
        self.assertEqual(dependency, {'module_name': '@minecraft/server-gametest', 'version': '1.0.0-beta'})
        self.assertEqual(overlay, original)
        self.assertEqual((runner.ROOT/'runtime/BP/manifest.json').read_bytes(), raw)

    def test_native_spawn_requires_explicit_fixture_mode(self):
        log = self.log('Player Spawned: TavernXpPickupQA xuid: , pfid:')
        self.assertFalse(runner.analyse_phase_log(log, 'first', True)['ok'])
        result = runner.analyse_phase_log(log, 'first', True, gametest=True)
        self.assertTrue(result['completed'])
        self.assertTrue(result['ok'])
        self.assertEqual(result['player_spawn_logs'], 1)

    def test_physical_connections_remain_forbidden(self):
        for event in ('Player connected: human', 'Player joined: human'):
            with self.subTest(event=event):
                result = runner.analyse_phase_log(self.log(event), 'first', True, gametest=True)
                self.assertFalse(result['ok'])
                self.assertEqual(result['player_connections'], 1)

    def test_fixture_must_disconnect_and_server_must_stop_normally(self):
        self.assertFalse(runner.analyse_phase_log(self.log(players=1), 'first', True, gametest=True)['ok'])
        self.assertFalse(runner.analyse_phase_log(self.log(), 'first', False, gametest=True)['ok'])
        self.assertFalse(runner.analyse_phase_log(self.log().replace('Quit correctly', ''), 'first', True, gametest=True)['ok'])


if __name__ == '__main__':
    unittest.main()
