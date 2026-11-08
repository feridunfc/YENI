"""VS06-D1 real-source B1 preview HTTP/UI acceptance (no live ETABS COM)."""
from __future__ import annotations

from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request,urlopen

from tbdy_next.web import make_handler
from test_vs06_b1_source_bridge import sources


class B1SourceUploadWebTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(self.root))
        self.thread=Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.host=f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown();self.server.server_close()
        self.thread.join(timeout=3)
        self.tmp.cleanup()

    def post(self,payload,headers=None):
        raw=json.dumps(payload,ensure_ascii=False).encode("utf-8")
        req=Request(self.host+"/api/vs06-b1-preview",data=raw,
                    headers={"Content-Type":"application/json",**(headers or {})},
                    method="POST")
        return urlopen(req,timeout=10)

    def test_full_XY_B1_upload_is_read_only_and_returns_html(self):
        a,b=sources()
        with self.post({"geometry":a,"wall_loads":b,
                        "options":{"wall_type":"BRITTLE","opening_fraction":"0.5"}}) as response:
            obj=json.load(response)
        r=obj["result"]
        self.assertEqual(r["source_candidate_wall_beams"],2)
        self.assertEqual(r["source_wall_load_rows"],2)
        self.assertEqual(r["b1_numerical"]["expected_story_direction_pairs"],2)
        self.assertEqual(r["formal_compliance"],"NOT_PROVEN")
        self.assertEqual(r["model"],a["model"])
        self.assertIn("b1 zayıf kat",obj["html"].lower())
        self.assertIn("0,15",obj["html"])
        self.assertEqual(list(self.root.iterdir()),[],
                         "B1 preview must not write a new receipt or ETABS file")

    def test_cross_origin_rejected_before_source_parsing(self):
        a,b=sources()
        with self.assertRaises(HTTPError) as cm:
            self.post({"geometry":a,"wall_loads":b,"options":{}},
                      headers={"Origin":"https://untrusted.example"})
        self.assertEqual(cm.exception.code,403)
        self.assertEqual(json.load(cm.exception)["error"],"CROSS_ORIGIN_DENIED")
        self.assertEqual(list(self.root.iterdir()),[])

    def test_cross_origin_invalid_json_never_reaches_source_parser(self):
        # A non-JSON body must still return 403, not 422, and Windows must
        # receive the HTTP response rather than WinError 10053/socket reset.
        req = Request(
            self.host+"/api/vs06-b1-preview",
            data=b"not-json-at-all",
            headers={"Origin":"https://untrusted.example",
                     "Content-Type":"application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as cm:
            urlopen(req,timeout=10)
        self.assertEqual(cm.exception.code,403)
        self.assertEqual(json.load(cm.exception)["error"],"CROSS_ORIGIN_DENIED")
        self.assertEqual(list(self.root.iterdir()),[])

    def test_cross_site_header_rejected_even_with_local_origin(self):
        req = Request(
            self.host+"/api/vs06-b1-preview",
            data=b"not-json-at-all",
            headers={"Origin":self.host,"Sec-Fetch-Site":"cross-site",
                     "Content-Type":"application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as cm:
            urlopen(req,timeout=10)
        self.assertEqual(cm.exception.code,403)
        self.assertEqual(json.load(cm.exception)["error"],"CROSS_ORIGIN_DENIED")

    def test_falsified_capture_rejected_without_result(self):
        a,b=sources()
        b["frame_load_object_probe"]["rows"][0]["LoadPattern"]="FAKE"
        with self.assertRaises(HTTPError) as cm:
            self.post({"geometry":a,"wall_loads":b,"options":{}})
        self.assertEqual(cm.exception.code,422)
        result=json.load(cm.exception)
        self.assertEqual(result["formal_compliance"],"NOT_PROVEN")

    def test_UI_has_dedicated_B1_panel_and_same_route(self):
        with urlopen(self.host+"/") as response:
            html=response.read().decode("utf-8")
        with urlopen(self.host+"/quick.js") as response:
            js=response.read().decode("utf-8")
        self.assertIn('id="b1GeometryFile"',html)
        self.assertIn('id="b1WallFile"',html)
        self.assertIn('id="b1Calculate"',html)
        self.assertIn('value="0.5"',html)
        self.assertIn("'/api/vs06-b1-preview'",js)
        self.assertIn("b1Download",js)
        self.assertEqual(html.count('id="runAllBtn"'),1)


if __name__=="__main__":
    unittest.main()
