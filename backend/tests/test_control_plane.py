import unittest

from backend.control_plane.models import Artifact, Component, Release
from backend.control_plane.orchestrator import ReleaseOrchestrator, promotion_order
from backend.control_plane.policy import Policy, PolicyError, evaluate_canary
from backend.ledger.writer import AuditLedger


class ControlPlaneTests(unittest.TestCase):
    def setUp(self):
        self.release = Release(
            release_id="27.9.0",
            artifact=Artifact("sha256:a", "abc", "sha256:s", "sha256:p", "sha256:sig"),
            components=[
                Component("database", "database"),
                Component("api", "service", depends_on=("database",)),
                Component("web", "service", depends_on=("api",)),
            ],
        )
        self.policy = Policy("staging", 1000, .02, .01, 500, 0)

    def test_dependency_order(self):
        self.assertEqual([x.name for x in promotion_order(self.release)], ["database", "api", "web"])

    def test_cycle_rejected(self):
        release = Release("x", self.release.artifact, [Component("a", "service", depends_on=("b",)), Component("b", "service", depends_on=("a",))])
        with self.assertRaises(Exception):
            promotion_order(release)

    def test_ledger_verifies(self):
        ledger = AuditLedger()
        ledger.append({"event_type": "A"})
        ledger.append({"event_type": "B"})
        self.assertTrue(ledger.verify())

    def test_canary_waits_for_sample(self):
        decision, reasons = evaluate_canary({"error_rate": .001}, {"requests": 1, "error_rate": .001}, self.policy)
        self.assertEqual(decision, "WAIT")
        self.assertIn("insufficient_sample", reasons)

    def test_admission_rejects_missing_attestation(self):
        controller = ReleaseOrchestrator(AuditLedger(), self.policy)
        evidence = {"artifact_verified": True, "signature_verified": True, "provenance_verified": True, "sbom_verified": True, "secrets_clean": True, "schema_compatible": True, "security_attestation": False, "contract_tests": True}
        with self.assertRaises(PolicyError):
            controller.validate(self.release, evidence)


if __name__ == "__main__":
    unittest.main()
