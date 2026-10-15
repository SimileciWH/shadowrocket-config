import importlib.util
import socket
import re
import unittest
import ipaddress
import json
import os
import shutil
import socketserver
import struct
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('setup_clash', ROOT / 'scripts/setup_clash_verge.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)

HOST = 'www.iesdouyin.com.bytedns1.com'
XHS_DOMAINS = {'+.xiaohongshu.com', '+.xhscdn.com', '+.xhscdn.net'}
XHS_CNAME_HOSTS = {
    'sns-video-v2.xhscdn.com.w.cdngslb.com',
    'sns-video-bd.xhscdn.com.c8c10c27.cm.bdydns.com',
    'hcdnv.ydbdxhsv6.cm.bdydns.com',
    'sns-video-v3.xhscdn.com.a.bdydns.com',
    'opencdnxhsvod1.jomodns.com',
    'sns-video-v6.xhscdn.com.volcgslb.com',
    'sns-video-v6.xhscdn.com.m.v19.volcgtm.com',
    'sns-video-hs.xhscdn.com.m.v05.volcgtm.com',
    'hcdnv.ydbdxhsv6.m.v05.volcgtm.com',
}
XHS_CNAME_FAMILIES = {
    '+.xhscdn.com.a.bdydns.com', '+.xhscdn.com.*.*.bdydns.com',
    '+.xhscdn.com.w.cdngslb.com', '+.xhscdn.com.volcgslb.com',
    '+.xhscdn.com.*.*.volcgtm.com', '+.ydbdxhsv6.*.bdydns.com',
    '+.ydbdxhsv6.*.*.volcgtm.com',
}


def records(*addresses):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443)) for ip in addresses]


class DouyinRealIPTests(unittest.TestCase):
    def test_real_core_matches_changing_xhs_aliases_without_excluding_vendor_zones(self):
        core = (os.environ.get('CLASH_MIHOMO_BIN') or shutil.which('mihomo')
                or '/Applications/Clash Verge.app/Contents/MacOS/verge-mihomo')
        if not Path(core).is_file():
            self.skipTest('需要本机真实 Mihomo；其余结构测试不代替运行态验证')

        class Upstream(socketserver.BaseRequestHandler):
            def handle(self):
                query, transport = self.request
                end = 12
                while query[end]:
                    end += query[end] + 1
                question = query[12:end + 5]
                answer = (b'\xc0\x0c' + struct.pack('!HHIH', 1, 1, 60, 4)
                          + socket.inet_aton('1.1.1.1'))
                transport.sendto(query[:2] + struct.pack('!HHHHH', 0x8180, 1, 1, 0, 0)
                                 + question + answer, self.client_address)

        def skip_name(data, offset):
            while data[offset]:
                if data[offset] & 0xc0 == 0xc0:
                    return offset + 2
                offset += data[offset] + 1
            return offset + 1

        def lookup(host, port):
            question = b''.join(bytes([len(label)]) + label.encode() for label in host.split('.'))
            query = struct.pack('!HHHHHH', 0x4312, 0x0100, 1, 0, 0, 0) + question + b'\0\0\1\0\1'
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                client.settimeout(0.5)
                deadline = time.monotonic() + 4
                while True:
                    client.sendto(query, ('127.0.0.1', port))
                    try:
                        data = client.recv(4096)
                        break
                    except socket.timeout:
                        if time.monotonic() >= deadline:
                            raise
            _, _, questions, answers, _, _ = struct.unpack('!HHHHHH', data[:12])
            offset = 12
            for _ in range(questions):
                offset = skip_name(data, offset) + 4
            addresses = []
            for _ in range(answers):
                offset = skip_name(data, offset)
                kind, _, _, size = struct.unpack('!HHIH', data[offset:offset + 10])
                offset += 10
                if kind == 1 and size == 4:
                    addresses.append(socket.inet_ntoa(data[offset:offset + size]))
                offset += size
            return addresses

        upstream = socketserver.UDPServer(('127.0.0.1', 0), Upstream)
        worker = threading.Thread(target=upstream.serve_forever, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory(prefix='xhs-core-dns-') as temp:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reservation:
                    reservation.bind(('127.0.0.1', 0))
                    port = reservation.getsockname()[1]
                dns = setup.load_yaml(setup.build_client_merge_content())['dns']
                dns.update({'listen': f'127.0.0.1:{port}', 'nameserver-policy': {},
                            'nameserver': [f'udp://127.0.0.1:{upstream.server_address[1]}']})
                path = Path(temp) / 'config.json'
                path.write_text(json.dumps({'dns': dns, 'mode': 'rule', 'mixed-port': 0,
                                            'tun': {'enable': False}, 'rules': ['MATCH,DIRECT'],
                                            'log-level': 'error'}))
                with (Path(temp) / 'core.log').open('w') as log:
                    process = subprocess.Popen([core, '-d', temp, '-f', str(path)], stdout=log, stderr=log)
                    try:
                        for host in [
                            'sns-video-v9.xhscdn.com.a.bdydns.com',
                            'sns-video-v9.xhscdn.com.w.cdngslb.com',
                            'sns-video-v9.xhscdn.com.m.v29.volcgtm.com',
                            'sns-video-bd.xhscdn.com.deadbeef.cm.bdydns.com',
                            'unseen.ydbdxhsv6.cm.bdydns.com',
                            'hcdnv.ydbdxhsv6.m.v99.volcgtm.com',
                        ]:
                            self.assertEqual(lookup(host, port), ['1.1.1.1'], host)
                        for host in ['unrelated.m.v19.volcgtm.com', 'other.bdydns.com',
                                     'evilxhscdn.com.w.cdngslb.com', 'api.anthropic.com',
                                     'sns-video-v6.xhscdn.com.w.cdngslb.com.attacker.example']:
                            answers = lookup(host, port)
                            self.assertTrue(answers, host)
                            self.assertTrue(all(ipaddress.ip_address(ip) in ipaddress.ip_network(
                                '198.18.0.0/15') for ip in answers), host)
                    finally:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
        finally:
            upstream.shutdown()
            upstream.server_close()
            worker.join(timeout=2)

    def test_xiaohongshu_real_ip_in_both_installers_and_generated_templates(self):
        self.assertTrue({'www.xiaohongshu.com', 'sns-video-v3.xhscdn.com',
                         'sns-video-v6.xhscdn.com'}.issubset(
            setup.REAL_IP_CHECK_HOSTS))
        for builder in (setup.build_client_merge_content, setup.build_work_merge_content):
            dns = setup.load_yaml(builder())['dns']
            self.assertEqual(dns['fake-ip-filter-mode'], 'blacklist')
            self.assertTrue((XHS_DOMAINS | XHS_CNAME_HOSTS | XHS_CNAME_FAMILIES).issubset(dns['fake-ip-filter']))
        for name in ('client_merge_template.yaml', 'work_merge_template.yaml', 'clash_merge_template.yaml'):
            dns = setup.load_yaml((ROOT / 'clash' / name).read_text())['dns']
            self.assertEqual(dns['fake-ip-filter-mode'], 'blacklist')
            self.assertTrue((XHS_DOMAINS | XHS_CNAME_HOSTS | XHS_CNAME_FAMILIES).issubset(dns['fake-ip-filter']))
        real = next(line for line in (ROOT / 'sr_ai_secure_final.conf').read_text().splitlines()
                    if line.startswith('always-real-ip ='))
        self.assertTrue(XHS_CNAME_HOSTS.issubset(real.split('=', 1)[1].strip().split(',')))

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
