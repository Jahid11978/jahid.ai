import unittest

from memory.encryption import EncryptionBoundary
from memory.gateway import MemoryGateway, MemoryType
from memory.provenance import ProvenanceLog


class MemoryFabricTests(unittest.IsolatedAsyncioTestCase):
    async def test_gateway_write_read_and_provenance(self):
        audit = ProvenanceLog()
        gateway = MemoryGateway(provenance=audit)
        record = await gateway.remember("user", "approved deployment procedure", MemoryType.PROCEDURAL, "jahid-ai", approved=True)
        found = await gateway.recall("user", "deployment procedure", "jahid-ai")
        self.assertEqual(found[0].memory_id, record.memory_id)
        self.assertEqual([event["action"] for event in audit.events], ["write", "read"])

    def test_authenticated_encryption_round_trip(self):
        boundary = EncryptionBoundary(b"x" * 32)
        token = boundary.protect("private memory")
        self.assertEqual(boundary.verify(token), "private memory")
        with self.assertRaises(Exception):
            boundary.verify(token[:-2] + "aa")


if __name__ == "__main__":
    unittest.main()
