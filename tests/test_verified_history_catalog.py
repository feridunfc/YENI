import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tbdy_next.archive_blobs import PACK_THRESHOLD, store_archive
from tbdy_next.history_catalog import listing, verification_key
from tbdy_next.receipts import ReceiptRun


class TestVerifiedHistoryCatalog(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt","Windows kernel directory notifications")
    def test_short_lived_request_threads_reuse_the_page_and_recheck_an_edited_blob(self):
        from threading import Thread
        from tbdy_next.history_catalog import ModalHistoryView
        with TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root/".archive-blobs"
            archive.mkdir()
            blob = archive/"data.gz"
            blob.write_bytes(b"A")
            calls = []
            def read(_):
                calls.append(1)
                return blob.read_bytes()
            view = ModalHistoryView(root,read)
            self.addCleanup(view.close)
            def request():
                out=[]
                thread = Thread(target=lambda:out.append(view.read()))
                thread.start()
                thread.join()
                return out[0]
            try:
                self.assertEqual(request(),b"A")
                self.assertEqual(request(),b"A")
                self.assertEqual(len(calls),1)
                stamp=blob.stat()
                blob.write_bytes(b"B")
                os.utime(blob,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
                self.assertEqual(request(),b"B")
                self.assertEqual(len(calls),2)
            finally:
                view.close()

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
            before_stat = blob.stat()
            blob.write_bytes(data[:-1] + bytes([data[-1]^1]))
            os.utime(blob,ns=(before_stat.st_atime_ns,before_stat.st_mtime_ns))
            self.assertNotEqual(verification_key(writer.root),before)

    def test_edited_stage_receipt_invalidates_even_at_the_same_length(self):
        with TemporaryDirectory() as temp:
            writer=ReceiptRun(Path(temp))
            (writer.root/"input.source").write_bytes(b"{}")
            receipt=writer.record("modal", {"status":"OK"}, input_sha256="a"*64)
            before=verification_key(writer.root)
            contents=receipt.read_bytes().replace(b'"OK"',b'"NO"')
            self.assertEqual(json.loads(contents)["payload"]["status"],"NO")
            stamp = receipt.stat()
            receipt.write_bytes(contents)
            os.utime(receipt,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
            self.assertNotEqual(verification_key(writer.root),before)
