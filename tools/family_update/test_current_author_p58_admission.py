"""reviewed integration reuses reviewed integration authors without reopening retired AMW gameplay."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from family_update import current_author_validation as m, stable_author_validation as dispatch


class P58Admission(unittest.TestCase):
    def test_fixed58_settings_and_all_stable_dispatches(self):
        config={'extension_stable_profile':'current-author-p58','extension_stable_validation':'fixture'}
        with patch.object(m.c,'CONFIG',config):
            self.assertTrue(m.selected())
            self.assertEqual(m.settings(),([1,0,58],'senluo-stable-author-20261019-p58','current_author_p58'))
        for name,args in [('verify_static',({},{})),('evidence_paths',(False,)),('bind_native',({},{})),('verify_installation',({},))]:
            with self.subTest(name=name),patch.object(m.c,'CONFIG',config),patch.object(m,name,return_value='exact58') as call:
                self.assertEqual(getattr(dispatch,name)(*args),'exact58');call.assert_called_once_with(*args)
        with patch.object(m.c,'CONFIG',{'extension_stable_profile':'current-author-p59'}):
            self.assertFalse(m.selected())
            with self.assertRaises(AssertionError):m.settings()

    def test_only58_source_records_use_new_owner_historical_names_stay_exact(self):
        self.assertEqual(m.REPOSITORY,'casama233/senluo-family-integration-private')
        for version in [55,56,57,58]:
            with self.subTest(version=version),patch.object(m.c,'CONFIG',{'extension_stable_profile':'current-author-p'+str(version)}):
                self.assertEqual(m.source_repository(),m.current_name(m.REPOSITORY) if version==58 else m.REPOSITORY)

    def fixture(self):
        before={'BP':{'manifest.json':'before','host-extensions/reviewed.json':'before-spec','scripts/kept.js':'same'},'RP':{'manifest.json':'before-rp','entity/inscription.json':'same'}}
        after=copy.deepcopy(before);after['BP'].update({'manifest.json':'after','host-extensions/reviewed.json':'after-spec',
            'scripts/host_api/fishing-water-particles.js':'helper','client-repairs/repair-plan.json':'plan'})
        after['RP']['manifest.json']='after-rp'
        for n in range(156):after['RP'][f'textures/integration/fishing-normal/kfv_item_{n:03}_normal.png']='normal'
        changed=['runtime/BP/host-extensions/reviewed.json','runtime/BP/manifest.json','runtime/RP/manifest.json']
        added=sorted(['runtime/BP/scripts/host_api/fishing-water-particles.js','runtime/BP/client-repairs/repair-plan.json',
            *[f'runtime/RP/textures/integration/fishing-normal/kfv_item_{n:03}_normal.png' for n in range(156)]])
        owned={'previous_files':before,'files':after,'exact_changed_paths':changed,'added_paths':added,'retired_paths':[]}
        catalog={key:copy.deepcopy(owned[key]) for key in ['exact_changed_paths','added_paths','retired_paths']};catalog['host_specs']={'reviewed.json':{}}
        return owned,catalog

    def validate(self,owned,catalog):
        with patch.object(m.c,'CONFIG',{'extension_stable_profile':'current-author-p58'}):m.validate_owned_conservation(owned,catalog)

    def test_only_identity_declarations_helper_plan_and156_normals_can_change(self):
        owned,catalog=self.fixture();self.validate(owned,catalog)
        for case in ['runtime','fauna','retire','normal-count','claim']:
            changed=copy.deepcopy(owned);policy=copy.deepcopy(catalog)
            if case=='runtime':
                changed['files']['BP']['scripts/kept.js']='changed';changed['exact_changed_paths'].append('runtime/BP/scripts/kept.js');changed['exact_changed_paths'].sort();policy['exact_changed_paths']=changed['exact_changed_paths']
            elif case=='fauna':
                changed['files']['BP']['scripts/fauna.js']='restored';changed['added_paths'].append('runtime/BP/scripts/fauna.js');changed['added_paths'].sort();policy['added_paths']=changed['added_paths']
            elif case=='retire':
                del changed['files']['RP']['entity/inscription.json'];changed['retired_paths']=['runtime/RP/entity/inscription.json'];policy['retired_paths']=changed['retired_paths']
            elif case=='normal-count':
                key='textures/integration/fishing-normal/kfv_item_000_normal.png';del changed['files']['RP'][key];changed['added_paths'].remove('runtime/RP/'+key);policy['added_paths']=changed['added_paths']
            else:changed['added_paths']=[]
            with self.subTest(case=case),self.assertRaises(AssertionError):self.validate(changed,policy)


if __name__=='__main__':unittest.main()
