import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import test_clash_profile_sync as fixtures

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('updater', ROOT / 'scripts/update_clash.py')
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)
SHA = 'a' * 40


class ReleaseTests(unittest.TestCase):
    def api_response(self, status='completed', conclusion='success'):
        return [{'sha': SHA}, {'workflow_runs': [{'id': 10, 'head_sha': SHA,
            'head_branch': 'main', 'event': 'push', 'status': status, 'conclusion': conclusion}]}]

    def test_only_verified_latest_commit_is_selected(self):
        with patch.object(updater, 'api', side_effect=self.api_response()):
            self.assertEqual(updater.latest_release(), SHA)

    def test_pending_or_failed_release_never_falls_back(self):
        for status, conclusion in [('in_progress', None), ('completed', 'failure')]:
            with patch.object(updater, 'api', side_effect=self.api_response(status, conclusion)):
                with self.assertRaises(ValueError):
                    updater.latest_release()

    def test_latest_failed_rerun_cannot_be_masked_by_old_success(self):
        responses = self.api_response()
        responses[1]['workflow_runs'].append(dict(responses[1]['workflow_runs'][0], id=11, conclusion='failure'))
        with patch.object(updater, 'api', side_effect=responses):
            with self.assertRaises(ValueError):
                updater.latest_release()

    def snapshot(self, directory):
        blobs = {path: (ROOT / path).read_bytes() for path in updater.FILES}
        tree = {'tree': [{'path': p, 'type': 'blob', 'sha': updater.blob_hash(data)} for p, data in blobs.items()]}
        urls = []
        def fetch(url):
            urls.append(url)
            self.assertIn(SHA, url)
            return next(data for p, data in blobs.items() if url.endswith('/' + p))
        with patch.object(updater, 'api', return_value=tree), patch.object(updater, 'fetch', side_effect=fetch):
            updater.download_snapshot(SHA, directory)
        return blobs, tree, urls

    def test_downloads_are_pinned_and_manifest_matches(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            blobs, _, urls = self.snapshot(directory)
            self.assertEqual(len(urls), 4)
            for p, data in blobs.items():
                self.assertEqual((directory / p).read_bytes(), data)
            self.assertEqual(json.loads((directory / 'release.json').read_text())['sha'], SHA)

    def test_corrupt_download_rejected(self):
        tree = {'tree': [{'path': p, 'type': 'blob', 'sha': 'b' * 40} for p in updater.FILES]}
        with tempfile.TemporaryDirectory() as temp, patch.object(updater, 'api', return_value=tree), patch.object(updater, 'fetch', return_value=b'old cache'):
            with self.assertRaises(ValueError):
                updater.download_snapshot(SHA, Path(temp))
            self.assertFalse((Path(temp) / 'release.json').exists())

    def test_snapshot_binds_urls_and_local_rule_cache(self):
        fixture = fixtures.ProfileSyncTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.snapshot(directory)
            with patch.dict(fixtures.setup.os.environ, {'SR_RELEASE_SHA': SHA, 'SR_RELEASE_DIR': temp}):
                plan = fixture.plan()
                merge = json.loads(plan['updates'][fixture.profiles / 'actual-merge.yaml'])
                for name in ('sr-direct', 'sr-proxy'):
                    provider = merge['rule-providers'][name]
                    self.assertIn('@' + SHA + '/', provider['url'])
                    cache = Path(provider['path'])
                    self.assertIn(SHA, cache.name)
                    self.assertIn(cache, plan['updates'])
                fixtures.setup.apply_deployment(plan)
                self.assertEqual(plan['updates'], fixture.plan()['updates'])

    def test_tampered_local_snapshot_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            self.snapshot(Path(temp))
            (Path(temp) / updater.FILES[1]).write_text('tampered')
            with patch.dict(fixtures.setup.os.environ, {'SR_RELEASE_SHA': SHA, 'SR_RELEASE_DIR': temp}):
                with self.assertRaises(ValueError):
                    fixtures.setup.release_snapshot()

    def test_branch_change_stops_before_installer_execution(self):
        with patch.object(updater, 'latest_release', return_value=SHA), patch.object(updater, 'download_snapshot'), patch.object(updater, 'api', return_value={'sha': 'b' * 40}), patch.object(updater.subprocess, 'call') as install:
            self.assertEqual(updater.main(), 1)
            install.assert_not_called()


if __name__ == '__main__':
    unittest.main()
