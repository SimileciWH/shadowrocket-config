#!/usr/bin/env python3
"""Verify Shadowrocket AUTO-CA-RESI fallback proxy group & zero secret leaks."""

from __future__ import annotations

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONF_PATH = ROOT / "sr_ai_secure_final.conf"
SNAP_PATH = ROOT / "versions" / "sr_ai_secure_final_20261129_1.conf"


def _parse_proxy_group_lines(text: str) -> dict[str, str]:
    groups: dict[str, str] = {}
    in_pg = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            in_pg = line == "[Proxy Group]"
            continue
        if in_pg and "=" in line:
            k, v = line.split("=", 1)
            groups[k.strip()] = v.strip()
    return groups


class FallbackProxyGroupTests(unittest.TestCase):
    def test_proxy_group_defines_auto_ca_resi_fallback_and_regex(self):
        text = CONF_PATH.read_text(encoding="utf-8")
        groups = _parse_proxy_group_lines(text)
        self.assertIn("AUTO-CA-RESI", groups)
        self.assertIn("PROXY", groups)

        auto_val = groups["AUTO-CA-RESI"]
        self.assertTrue(auto_val.startswith("fallback,"))
        self.assertIn("url=http://www.gstatic.com/generate_204", auto_val)
        self.assertIn("interval=180", auto_val)
        self.assertIn("timeout=5", auto_val)
        m = re.search(r"policy-regex-filter=(.+)$", auto_val)
        self.assertIsNotNone(m)
        pat_raw = m.group(1)
        if pat_raw.startswith("(?i)"):
            pat = re.compile(pat_raw[4:], re.IGNORECASE)
        else:
            pat = re.compile(pat_raw)

        # Must match primary BWG and standby DediOne CA residential nodes
        for should_match in (
            "BWG-PXY4FREE-CALIFORNIA",
            "DediOne-LAX-CMIN2-CA-Resi",
            "bwg_california_resi",
            "dedione-lax-ca-resi",
        ):
            self.assertIsNotNone(pat.search(should_match), f"Expected regex to match {should_match}")

        # Must reject direct datacenter nodes, RU node, and corp tunnel
        for should_reject in (
            "justg-vps-RU-direct",
            "CORP-WINDOWS",
            "DediOne-LAX-CMIN2-Direct",
            "BWG-VPS-DIRECT",
        ):
            self.assertIsNone(pat.search(should_reject), f"Expected regex to reject {should_reject}")

        proxy_val = groups["PROXY"]
        self.assertTrue(proxy_val.startswith("select,AUTO-CA-RESI"))
        self.assertIn("policy-regex-filter=.*", proxy_val)

    def test_snapshot_and_no_private_ips_or_secrets(self):
        text = CONF_PATH.read_text(encoding="utf-8")
        self.assertIn("# Shadowrocket Config Version: 2026.11.29.1", text)
        self.assertTrue(SNAP_PATH.exists())
        self.assertEqual(SNAP_PATH.read_text(encoding="utf-8"), text)

        forbidden_markers = (
            "95.169.1.190",
            "166.1.247.138",
            "24.249.245.244",
            "43.172.71.245",
            "pxy4free",
            "vless://",
            "4LLD0OQWTX5LPPS1",
        )
        files_to_scan = [CONF_PATH, SNAP_PATH] + sorted((ROOT / "clash").glob("*.yaml"))
        for fp in files_to_scan:
            content = fp.read_text(encoding="utf-8")
            for marker in forbidden_markers:
                self.assertNotIn(marker.lower(), content.lower(), f"Forbidden marker {marker} in {fp.name}")


if __name__ == "__main__":
    unittest.main()
