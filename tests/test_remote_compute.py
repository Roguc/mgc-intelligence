import unittest
from types import SimpleNamespace
from remote_compute import MODEL, NODE_NAME, TailscaleComputeLifecycle
class TailscaleComputeTests(unittest.TestCase):
 def tailnet(self,running=True): return lambda args,**kwargs: SimpleNamespace(returncode=0 if running else 1,stdout='{"BackendState":"Running"}' if running else '')
 def test_ready_requires_tailnet_and_model(self):
  r=TailscaleComputeLifecycle(runner=self.tailnet(),probe=lambda url:{"models":[{"name":MODEL}]},tailscale_path="tailscale");self.assertTrue(r.inspect().ready);self.assertEqual(f"http://{NODE_NAME}:11434",r.endpoint_url)
 def test_offline_fails_closed(self):
  r=TailscaleComputeLifecycle(runner=self.tailnet(False),probe=lambda url:self.fail("must not contact appliance"),tailscale_path="tailscale");self.assertEqual("OFFLINE",r.inspect().state)
 def test_appliance_starting_is_executive(self):
  r=TailscaleComputeLifecycle(runner=self.tailnet(),probe=lambda url:(_ for _ in ()).throw(OSError()),tailscale_path="tailscale");self.assertEqual("STARTING",r.inspect().state)
 def test_model_missing_is_not_ready(self):
  r=TailscaleComputeLifecycle(runner=self.tailnet(),probe=lambda url:{"models":[]},tailscale_path="tailscale");self.assertEqual("STARTING",r.inspect().state)
