from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

from remote_compute import ComputeStatus, RemoteComputeLifecycle, VastDiscovery, _persistent_user_environment


class RemoteComputeTests(unittest.TestCase):
    def endpoint(self, status="running", host="ssh1.vast.ai", port=22001):
        return {"instances": {"id": 7, "actual_status": status, "ssh_host": host, "ssh_port": port}}

    def test_discovery_uses_current_endpoint_returned_by_vast(self):
        discovery = VastDiscovery("token", "7", lambda url, headers: self.endpoint(host="ssh99.vast.ai", port=31000))
        found = discovery.discover()
        self.assertEqual(("ssh99.vast.ai", 31000), (found.host, found.port))

    def test_stopped_instance_has_executive_message(self):
        discovery = VastDiscovery("token", "7", lambda url, headers: self.endpoint(status="stopped"))
        with self.assertRaisesRegex(Exception, "Inicie Vast"):
            discovery.discover()

    def test_prepare_recovers_transport_and_waits_for_model(self):
        calls, responses = [], [{"models": []}, {"models": []}, {"models": [{"name": "qwen3:14b"}]}]
        discovery = VastDiscovery("token", "7", lambda url, headers: self.endpoint())
        lifecycle = RemoteComputeLifecycle(
            discovery, runner=lambda args, **kwargs: calls.append(args) or SimpleNamespace(returncode=0),
            probe=lambda url: responses.pop(0) if responses else {"models": [{"name": "qwen3:14b"}]},
            sleep=lambda _: None, key_path=Path(__file__), known_hosts=Path("/tmp/lnh-known-hosts"),
        )
        status = lifecycle.prepare(timeout_seconds=1)
        self.assertTrue(status.ready)
        self.assertEqual(1, len(calls))  # Remote Ollama recovery; an existing transport was reusable.

    def test_model_missing_is_preparing_not_ready(self):
        lifecycle = RemoteComputeLifecycle(probe=lambda url: {"models": []})
        self.assertEqual("PREPARING", lifecycle.inspect().state)

    def test_connection_interruption_is_safe_unavailable(self):
        lifecycle = RemoteComputeLifecycle(probe=lambda url: (_ for _ in ()).throw(OSError("offline")))
        status = lifecycle.inspect()
        self.assertEqual("UNAVAILABLE", status.state)
        self.assertIn("Cómputo remoto", status.executive_message)

    def test_endpoint_change_is_taken_from_each_vast_response(self):
        first = VastDiscovery("token", "7", lambda url, headers: self.endpoint(host="ssh-old.vast.ai", port=20001))
        second = VastDiscovery("token", "7", lambda url, headers: self.endpoint(host="ssh-new.vast.ai", port=30001))
        self.assertNotEqual(first.discover(), second.discover())

    def test_remote_service_startup_is_retried_within_the_bounded_wait(self):
        attempts = []
        discovery = VastDiscovery("token", "7", lambda url, headers: self.endpoint())
        def runner(args, **kwargs):
            attempts.append(args)
            return SimpleNamespace(returncode=1 if len(attempts) == 1 else 0)
        probes = [{"models": []}, {"models": [{"name": "qwen3:14b"}]}]
        lifecycle = RemoteComputeLifecycle(
            discovery, runner=runner, probe=lambda url: probes.pop(0) if probes else {"models": [{"name": "qwen3:14b"}]},
            sleep=lambda _: None, key_path=Path(__file__), known_hosts=Path("/tmp/lnh-known-hosts"),
        )
        self.assertTrue(lifecycle.prepare(timeout_seconds=1).ready)
        self.assertEqual(2, len(attempts))

    def test_no_credential_fails_closed_without_transport_attempt(self):
        from unittest.mock import patch
        with patch("remote_compute._persistent_user_environment", return_value=None):
            discovery = VastDiscovery(None, "7")
        lifecycle = RemoteComputeLifecycle(discovery, runner=lambda *args, **kwargs: self.fail("SSH must not run"), probe=lambda url: (_ for _ in ()).throw(OSError("offline")))
        self.assertEqual("UNAVAILABLE", lifecycle.prepare(timeout_seconds=1).state)

    def test_process_environment_is_preferred_for_credential(self):
        from unittest.mock import patch
        with patch.dict("os.environ", {"LNH_VAST_API_KEY": "present"}, clear=True):
            self.assertEqual("present", _persistent_user_environment("LNH_VAST_API_KEY"))
