import http.server
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mesurer_charge  # noqa: E402


class _Page(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - nom imposé par http.server
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


class TestMesurerCharge(unittest.TestCase):
    def test_compte_les_reponses_d_un_serveur_local(self):
        serveur = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Page)
        threading.Thread(target=serveur.serve_forever, daemon=True).start()
        try:
            r = mesurer_charge.mesurer(
                f"http://127.0.0.1:{serveur.server_port}/annonces?q=b", 2, 0.5
            )
        finally:
            serveur.shutdown()
        self.assertGreater(r["debit"], 0)
        self.assertEqual(set(r["codes"]), {200})


if __name__ == "__main__":
    unittest.main()
