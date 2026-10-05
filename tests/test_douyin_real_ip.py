import importlib.util
import socket
import re
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('setup_clash', ROOT / 'scripts/setup_clash_verge.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)

HOST = 'www.iesdouyin.com.bytedns1.com'


def records(*addresses):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443)) for ip in addresses]


class DouyinRealIPTests(unittest.TestCase):
    def test_cname_covered_in_installer_and_both_builders(self):
        self.assertIn(HOST, setup.DOUYIN_REAL_IP_DOMAINS)
        for builder in (setup.build_client_merge_content, setup.build_work_merge_content):
            self.assertIn('"' + HOST + '"', builder())

    def test_generated_templates_and_shadowrocket_cover_same_aliases(self):
        for name in ('client_merge_template.yaml', 'work_merge_template.yaml', 'clash_merge_template.yaml'):
            text = (ROOT / 'clash' / name).read_text()
            domains = re.findall(r'^\s+- "([^"\n]+)"$', text, re.MULTILINE)
            self.assertTrue(set(setup.DOUYIN_CNAME_HOSTS).issubset(domains))
        text = (ROOT / 'sr_ai_secure_final.conf').read_text()
        real = next(line for line in text.splitlines() if line.startswith('always-real-ip ='))
        domains = [part.strip() for part in real.split('=', 1)[1].split(',')]
        self.assertTrue(set(setup.DOUYIN_CNAME_HOSTS).issubset(domains))

    def test_blacklist_merge_idempotent_and_preserves_unrelated_config(self):
        raw = 'dns:\n  fake-ip-filter-mode: blacklist\n  fake-ip-filter:\n    - localhost\nmode: rule\n'
        first, changed, _ = setup.merge_fake_ip_filter_content(raw, setup.DOUYIN_REAL_IP_DOMAINS)
        self.assertTrue(changed)
        self.assertIn(HOST, first)
        self.assertIn('mode: rule', first)
        second, changed, _ = setup.merge_fake_ip_filter_content(first, setup.DOUYIN_REAL_IP_DOMAINS)
        self.assertEqual(first, second)
        self.assertFalse(changed)

    def test_whitelist_removes_observed_alias_only(self):
        raw = f'dns:\n  fake-ip-filter-mode: whitelist\n  fake-ip-filter:\n    - {HOST}\n    - unrelated.example\n'
        merged, _, _ = setup.merge_fake_ip_filter_content(raw, setup.DOUYIN_REAL_IP_DOMAINS)
        self.assertNotIn(HOST, merged)
        self.assertIn('unrelated.example', merged)

    def test_system_fake_ip_cannot_be_masked_by_public_dig(self):
        with patch.object(setup.socket, 'getaddrinfo', return_value=records('198.18.0.25')), patch.object(setup.subprocess, 'run') as dig:
            addresses, public = setup.system_dns_status('www.iesdouyin.com')
        self.assertEqual(addresses, ['198.18.0.25'])
        self.assertFalse(public)
        dig.assert_not_called()

    def test_mixed_or_other_nonpublic_answers_fail(self):
        for answer in [records('1.1.1.1', '198.18.0.25'), records('127.0.0.1'), records('10.0.0.1'), records('::1'), []]:
            with self.subTest(answer=answer), patch.object(setup.socket, 'getaddrinfo', return_value=answer):
                self.assertFalse(setup.system_dns_status('www.iesdouyin.com')[1])

    def test_all_public_answers_pass(self):
        with patch.object(setup.socket, 'getaddrinfo', return_value=records('1.1.1.1', '8.8.8.8')):
            self.assertTrue(setup.system_dns_status('www.iesdouyin.com')[1])

    def test_lookup_error_is_not_success(self):
        with patch.object(setup.socket, 'getaddrinfo', side_effect=socket.gaierror()):
            self.assertEqual(setup.system_dns_status('www.iesdouyin.com'), ([], False))


if __name__ == '__main__':
    unittest.main()
