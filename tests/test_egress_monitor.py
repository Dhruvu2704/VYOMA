"""Real runtime egress monitor tests.

Proves the psutil-backed monitor (``backend.services.egress_monitor``) is
genuinely verifiable rather than a decorative "0 KB sent" label:

- loopback destinations (the local Ollama instance) classify as LOCAL,
- any non-loopback destination classifies as EXTERNAL,
- snapshots carry real live connection data with matching counts,
- the external-observed count stays 0 during a real local Ollama request,
- interface summaries are real psutil data.

Run from repo root:

    python -m unittest tests.test_egress_monitor -v
"""

from __future__ import annotations

import threading
import time
import types
import unittest
from urllib.parse import urlsplit

from ai_agent.config import load_ollama_config
from ai_agent.router.model_router import build_local_model_router
from ai_agent.router.ollama_provider import list_local_models

from backend.services.egress_monitor import (
    EgressMonitor,
    _classify_connection,
    network_interface_summary,
)


def _conn(raddr: tuple | None):
    """A minimal stand-in for a psutil connection record."""
    if raddr is None:
        return types.SimpleNamespace(laddr=types.SimpleNamespace(ip="127.0.0.1", port=0), raddr=())
    ip, port = raddr
    return types.SimpleNamespace(
        laddr=types.SimpleNamespace(ip="127.0.0.1", port=port),
        raddr=types.SimpleNamespace(ip=ip, port=port),
    )


class EgressMonitorClassifyTests(unittest.TestCase):
    def test_loopback_destinations_are_local(self) -> None:
        self.assertEqual(_classify_connection(_conn(("127.0.0.1", 11434))), "local")
        self.assertEqual(_classify_connection(_conn(("127.0.0.2", 11434))), "local")
        self.assertEqual(_classify_connection(_conn(("::1", 11434))), "local")

    def test_listening_connections_with_no_destination_are_local(self) -> None:
        self.assertEqual(_classify_connection(_conn(None)), "local")

    def test_external_destination_is_detected(self) -> None:
        self.assertEqual(_classify_connection(_conn(("8.8.8.8", 443))), "external")
        self.assertEqual(_classify_connection(_conn(("192.168.1.10", 80))), "external")


class EgressMonitorRuntimeTests(unittest.TestCase):
    def test_snapshot_shape_and_honest_zero(self) -> None:
        monitor = EgressMonitor()
        snap = monitor.snapshot()
        self.assertEqual(snap["external_observed_since_start"], 0)
        self.assertEqual(
            snap["external_connection_count"],
            len(snap["external_connections"]),
        )
        self.assertEqual(
            snap["local_connection_count"],
            len(snap["local_connections"]),
        )
        self.assertIsNotNone(snap["sampled_at"])
        for conn in snap["external_connections"]:
            self.assertIsNotNone(conn["raddr"])
            self.assertNotEqual(conn["raddr"]["ip"].split(".")[0], "127")
            self.assertNotEqual(conn["raddr"]["ip"], "::1")
        for conn in snap["local_connections"]:
            self.assertIn(conn["family"], {"IPv4", "IPv6"})
        for conn in snap["external_connections"]:
            self.assertIn(conn["family"], {"IPv4", "IPv6"})

    def test_interface_summary_is_real(self) -> None:
        ifaces = network_interface_summary()
        self.assertIsInstance(ifaces, list)
        for iface in ifaces:
            self.assertIn("name", iface)
            self.assertIn("is_up", iface)
            self.assertIn("addresses", iface)
            self.assertIsInstance(iface["is_up"], bool)
            for addr in iface["addresses"]:
                self.assertIn("family", addr)
                self.assertNotIn(addr["family"], {"2", "10", "23", "-1"})

    def test_external_observed_stays_zero_during_real_local_ollama_request(self) -> None:
        config = load_ollama_config()
        if list_local_models(config)["status"] != "online":
            self.skipTest("local Ollama not reachable")
        port = urlsplit(config.base_url).port or 11434

        monitor = EgressMonitor()
        provider = build_local_model_router(config=config).select_provider("reasoning")

        holder: dict = {}
        errors: list = []

        def reason() -> None:
            try:
                holder["response"] = provider.generate(
                "Write a short justification of why this permit set is safe, "
                "referencing isolation and hot work controls."
            )
            except Exception as exc:  # noqa: BLE001 - surfaced to the test body
                errors.append(exc)

        worker = threading.Thread(target=reason)
        worker.start()

        # Sample at fine cadence for the whole duration of the real request so
        # the loopback Ollama connection is actually observed in-flight.
        seen_local_targets: set = set()
        samples_taken = 0
        while worker.is_alive():
            snap = monitor.snapshot()
            samples_taken += 1
            self.assertEqual(snap["external_observed_since_start"], 0)
            self.assertEqual(snap["external_connection_count"], 0)
            seen_local_targets.update(
                (c["raddr"]["ip"], c["raddr"]["port"])
                for c in snap["local_connections"]
                if c["raddr"]
            )
            time.sleep(0.03)
        worker.join(timeout=120)

        snap_after = monitor.snapshot()
        self.assertEqual(snap_after["external_observed_since_start"], 0)
        self.assertEqual(snap_after["external_connection_count"], 0)
        seen_local_targets.update(
            (c["raddr"]["ip"], c["raddr"]["port"])
            for c in snap_after["local_connections"]
            if c["raddr"]
        )

        self.assertGreater(samples_taken, 0)
        self.assertEqual(errors, [])
        self.assertTrue(holder["response"].ok, holder["response"].error)

        # Zero-egress held on every sample taken during the request, and the
        # loopback connection to the local Ollama instance was observed.
        self.assertIn(
            ("127.0.0.1", port),
            seen_local_targets,
            f"expected a loopback connection to 127.0.0.1:{port} during/after the request; got {seen_local_targets}",
        )


if __name__ == "__main__":
    unittest.main()