import unittest

from backend.memory.encryption import EncryptionBoundary
from backend.memory.gateway import AllowAllPolicy, MemoryGateway, MemoryType
from backend.memory.provenance import ProvenanceLog


class MemoryFabricTests(unittest.IsolatedAsyncioTestCase):
    async def test_gateway_write_read_and_provenance(self):
        audit = ProvenanceLog()
        gateway = MemoryGateway(policy=AllowAllPolicy(), provenance=audit)
        record = await gateway.remember("user", "approved deployment procedure", MemoryType.PROCEDURAL, "jahid-ai", approved=True)
        found = await gateway.recall("user", "deployment procedure", "jahid-ai")
        self.assertEqual(found[0].memory_id, record.memory_id)
        self.assertEqual([event["action"] for event in audit.events], ["write", "read"])

    async def test_gateway_denies_without_policy(self):
        gateway = MemoryGateway()
        with self.assertRaises(PermissionError):
            await gateway.recall("user", "private", "jahid-ai")

    def test_authenticated_encryption_round_trip(self):
        boundary = EncryptionBoundary(b"x" * 32)
        token = boundary.protect("private memory")
        self.assertEqual(boundary.verify(token), "private memory")
        with self.assertRaises(Exception):
            boundary.verify(token[:-2] + "aa")


if __name__ == "__main__":
    unittest.main()
