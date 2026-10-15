"""Verify the installed kubectl sends DeleteOptions, without touching a cluster."""
import json
import shutil
import subprocess
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class KubectlDeleteBodyTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which("kubectl"), "kubectl is unavailable")
    def test_raw_delete_sends_uid_precondition_from_stdin(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def handle_expect_100(self):
                self.send_response_only(100)
                self.end_headers()
                return True

            def do_DELETE(self):
                if self.headers.get("Transfer-Encoding") == "chunked":
                    chunks = []
                    while True:
                        size = int(self.rfile.readline().strip().split(b";")[0], 16)
                        if not size:
                            self.rfile.readline()
                            break
                        chunks.append(self.rfile.read(size))
                        self.rfile.read(2)
                    raw = b"".join(chunks)
                else:
                    raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                received.append((self.path, json.loads(raw)))
                body = b'{"apiVersion":"v1","kind":"Status","status":"Success"}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *_args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            path = "/api/v1/namespaces/test/services/sample"
            body = {"apiVersion": "v1", "kind": "DeleteOptions", "preconditions": {"uid": "recorded-uid"}}
            result = subprocess.run(["kubectl", "--kubeconfig=/dev/null", f"--server=http://127.0.0.1:{server.server_port}",
                                     "delete", "--raw", path, "-f", "-"], input=json.dumps(body), text=True,
                                    capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(received, [(path, body)])
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)
