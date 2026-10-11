#!/usr/bin/env python3
"""Serve the playable single-file build at / with iframe-friendly headers."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import gzip
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, 'vila-de-goblins-jogavel.html')
os.chdir(ROOT)

GAME_BYTES = open(GAME, 'rb').read()
GAME_GZIP = gzip.compress(GAME_BYTES, compresslevel=5)


class Handler(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path in ('/', '/index.html', '/index.htm', '/play', '/play.html',
                    '/vila-de-goblins-jogavel.html'):
            self._send_game()
            return
        return super().do_GET()

    def do_HEAD(self):
        path = self.path.split('?', 1)[0]
        if path in ('/', '/index.html', '/index.htm', '/play', '/play.html',
                    '/vila-de-goblins-jogavel.html'):
            self._send_game(body=False)
            return
        return super().do_HEAD()

    def _send_game(self, body=True):
        accept = self.headers.get('Accept-Encoding', '')
        use_gz = 'gzip' in accept
        data = GAME_GZIP if use_gz else GAME_BYTES
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        if use_gz:
            self.send_header('Content-Encoding', 'gzip')
        self.send_header('Vary', 'Accept-Encoding')
        self.end_headers()
        if body:
            self.wfile.write(data)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    httpd = ThreadingHTTPServer(('0.0.0.0', port), Handler)
    print(f'serving game on 0.0.0.0:{port} ({len(GAME_BYTES)} bytes, gzip {len(GAME_GZIP)})',
          flush=True)
    httpd.serve_forever()


if __name__ == '__main__':
    main()
