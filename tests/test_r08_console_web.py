"""Right-side product console HTTP delivery, without ETABS or research scripts."""
from __future__ import annotations

from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.request import urlopen
import unittest

from tbdy_next.web import make_handler


class EngineConsoleHTTPTests(unittest.TestCase):
    def test_console_below_not_ready_is_served_in_real_ui(self):
        with TemporaryDirectory() as directory:
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0), make_handler(Path(directory)))
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                with urlopen(base + "/") as response:
                    html = response.read().decode("utf-8")
                with urlopen(base + "/engine-console.js") as response:
                    self.assertIn("javascript", response.headers["Content-Type"])
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                    script = response.read().decode("utf-8")
                with urlopen(base + "/quick.js") as response:
                    client = response.read().decode("utf-8")
                self.assertIn('id="engineConsoleMessages"', html)
                self.assertIn('role="log"', html)
                self.assertLess(
                    html.index('Mühendislik kabulü<strong>NOT_READY'),
                    html.index('<section class="engine-console"'))
                self.assertIn('/engine-console.js', html)
                self.assertIn("window.engineConsole", script)
                self.assertIn("textContent = value", script)
                self.assertIn("LIVE_ETABS_UNITS_KN_M_C_REQUIRED", client)
                self.assertIn("ETABS BİRİM", client)
                self.assertIn("eventLog('error', 'BİRLEŞİK TARAMA'", client)
                self.assertEqual(html.count('id="runAllBtn"'), 1,
                                 "Console may not add another live button")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
