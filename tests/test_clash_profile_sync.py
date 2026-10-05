import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('setup_sync', Path(__file__).resolve().parents[1] / 'scripts/setup_clash_verge.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class ProfileSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profiles = self.root / 'profiles'
        self.profiles.mkdir()
        self.index = {'current': 'active', 'items': [
            {'uid': 'old', 'name': 'same.yaml', 'type': 'local', 'file': 'old.yaml'},
            {'uid': 'active', 'name': 'same.yaml', 'type': 'remote', 'file': '1759600109019.yaml', 'option': {'merge': 'm', 'rules': 'r'}},
            {'uid': 'm', 'type': 'merge', 'file': 'actual-merge.yaml'},
            {'uid': 'r', 'type': 'rules', 'file': 'actual-rules.yaml'}]}
        self.write(self.root / 'profiles.yaml', self.index)
        self.write(self.profiles / '1759600109019.yaml', {'proxies': [{'name': 'test-node', 'type': 'socks5', 'server': '127.0.0.1', 'port': 9}], 'proxy-groups': [{'name': 'PROXY', 'type': 'select', 'proxies': ['test-node']}], 'rules': ['MATCH,PROXY']})
        self.write(self.profiles / 'old.yaml', {'unchanged': True})
        self.write(self.profiles / 'actual-merge.yaml', {'rule-providers': {'custom': {'type': 'inline', 'behavior': 'classical', 'payload': ['DOMAIN,custom.example']}}, 'prepend-rules': ['RULE-SET,sr-proxy,节点选择']})
        self.write(self.profiles / 'actual-rules.yaml', {'prepend': ['RULE-SET,sr-proxy,节点选择', 'DOMAIN,keep.example,DIRECT'], 'append': ['DOMAIN,last.example,DIRECT'], 'delete': ['DOMAIN,remove.example,DIRECT']})

    def write(self, path, data):
        path.write_text(json.dumps(data))

    def plan(self, work=False):
        with patch.object(setup.subprocess, 'run') as run:
            run.return_value.returncode = 0
            return setup.prepare_deployment(self.root, work)

    def test_current_uid_file_metadata_and_preservation(self):
        plan = self.plan()
        self.assertNotIn(self.profiles / 'old.yaml', plan['updates'])
        rules = json.loads(plan['updates'][self.profiles / 'actual-rules.yaml'])
        self.assertIn('RULE-SET,sr-proxy,PROXY', rules['prepend'])
        self.assertNotIn('RULE-SET,sr-proxy,节点选择', rules['prepend'])
        self.assertIn('DOMAIN,keep.example,DIRECT', rules['prepend'])
        self.assertEqual(rules['append'], ['DOMAIN,last.example,DIRECT'])
        self.assertEqual(rules['delete'], ['DOMAIN,remove.example,DIRECT'])
        merge = json.loads(plan['updates'][self.profiles / 'actual-merge.yaml'])
        self.assertNotIn('prepend-rules', merge)
        self.assertNotIn('prepend-proxy-groups', merge)
        self.assertIn('custom', merge['rule-providers'])

    def test_missing_file_does_not_choose_latest(self):
        (self.profiles / '1759600109019.yaml').unlink()
        with self.assertRaises(ValueError):
            self.plan()

    def test_missing_current_fails_without_writing(self):
        self.index['current'] = 'missing'
        self.write(self.root / 'profiles.yaml', self.index)
        with self.assertRaises(ValueError):
            self.plan()
        self.assertFalse(list(self.root.glob('sr-backup-*')))

    def test_no_group_never_falls_back_to_direct(self):
        self.write(self.profiles / '1759600109019.yaml', {'rules': ['MATCH,DIRECT']})
        with self.assertRaises(ValueError):
            self.plan()

    def test_missing_extensions_created_and_second_run_idempotent(self):
        self.index['items'][1]['option'] = {}
        self.write(self.root / 'profiles.yaml', self.index)
        first = self.plan()
        setup.apply_deployment(first)
        second = self.plan()
        self.assertEqual(first['updates'], second['updates'])
        self.assertTrue(list(self.root.glob('sr-backup-*')))

    def test_custom_invalid_target_fails_before_write(self):
        self.write(self.profiles / 'actual-rules.yaml', {'prepend': ['DOMAIN,custom.example,missing']})
        with self.assertRaises(ValueError):
            self.plan()

    def test_core_failure_prevents_changes(self):
        before = (self.root / 'profiles.yaml').read_bytes()
        with patch.dict(setup.os.environ, {'CLASH_MIHOMO_BIN': '/test/core'}), patch.object(setup.subprocess, 'run') as run:
            run.return_value.returncode = 1
            with self.assertRaises(ValueError):
                setup.prepare_deployment(self.root)
        self.assertEqual(before, (self.root / 'profiles.yaml').read_bytes())

    def test_parallel_edit_prevents_overwrite(self):
        plan = self.plan()
        path = self.profiles / 'actual-rules.yaml'
        path.write_text('prepend: []\n')
        with self.assertRaises(ValueError):
            setup.apply_deployment(plan)
        self.assertEqual(path.read_text(), 'prepend: []\n')

    def test_write_failure_rolls_back(self):
        plan = self.plan()
        before = {p: p.read_bytes() for p in plan['updates']}
        replace = setup.os.replace
        calls = []
        def fail_second(src, dst):
            calls.append(dst)
            if len(calls) == 2:
                raise OSError('simulated write failure')
            replace(src, dst)
        with patch.object(setup.os, 'replace', side_effect=fail_second):
            with self.assertRaises(OSError):
                setup.apply_deployment(plan)
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            setup.resolve_profile_file(self.profiles, 'uid', '../profiles.yaml')

    def test_emoji_and_quoted_group_names(self):
        path = self.profiles / '1759600109019.yaml'
        data = json.loads(path.read_text())
        data['proxy-groups'][0]['name'] = '🚀 "海外"'
        data['rules'] = ['MATCH,🚀 "海外"']
        self.write(path, data)
        rules = json.loads(self.plan()['updates'][self.profiles / 'actual-rules.yaml'])
        self.assertIn('RULE-SET,sr-proxy,🚀 "海外"', rules['prepend'])

    def test_work_mode_uses_supported_extensions(self):
        plan = self.plan(True)
        index = json.loads(plan['updates'][self.root / 'profiles.yaml'])
        current = next(i for i in index['items'] if i['uid'] == 'active')
        self.assertIn('groups', current['option'])
        self.assertIn('proxies', current['option'])
        merge = json.loads(plan['updates'][self.profiles / 'actual-merge.yaml'])
        self.assertNotIn('proxies', merge)
        self.assertIn('sr-company', merge['rule-providers'])


if __name__ == '__main__':
    unittest.main()
