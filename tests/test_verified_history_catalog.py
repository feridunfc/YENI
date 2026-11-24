import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tbdy_next.archive_blobs import PACK_THRESHOLD, store_archive
from tbdy_next.history_catalog import listing, verification_key
from tbdy_next.receipts import ReceiptRun


class TestVerifiedHistoryCatalog(unittest.TestCase):
    def test_changed_shared_blob_invalidates_an_indexed_run(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            writer = ReceiptRun(root)
            store_archive(writer.root/"input.source", b"s"*PACK_THRESHOLD)
            writer.record("modal", {"case":"Modal","status":"reference"}, input_sha256="f"*64)
            self.assertEqual(listing(root,modal=True)[0]["run_id"],writer.run_id)
            before = verification_key(writer.root)
            blob, = (root/".archive-blobs").glob("*.gz")
            data = blob.read_bytes()
            blob.write_bytes(data[:-1] + bytes([data[-1]^1]))
            self.assertNotEqual(verification_key(writer.root),before)

    def test_edited_stage_receipt_invalidates_even_at_the_same_length(self):
        with TemporaryDirectory() as temp:
            writer=ReceiptRun(Path(temp))
            (writer.root/"input.source").write_bytes(b"{}")
            receipt=writer.record("modal", {"status":"OK"}, input_sha256="a"*64)
            before=verification_key(writer.root)
            contents=receipt.read_bytes().replace(b'"OK"',b'"NO"')
            self.assertEqual(json.loads(contents)["payload"]["status"],"NO")
            receipt.write_bytes(contents)
            self.assertNotEqual(verification_key(writer.root),before)
