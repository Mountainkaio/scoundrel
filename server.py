from http.server import HTTPServer, SimpleHTTPRequestHandler


class COOPCOEPHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # CORS header
        self.send_header("Access-Control-Allow-Origin", "*")
        # Required for SharedArrayBuffer / crossOriginIsolated
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Resource-Policy", "cross-origin")
        super().end_headers()


if __name__ == "__main__":
    host = "localhost"
    port = 8000

    print(f"Serving at http://{host}:{port}")
    HTTPServer((host, port), COOPCOEPHandler).serve_forever()
