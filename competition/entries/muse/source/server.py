import http.server, os, re
ROOT = os.path.dirname(os.path.abspath(__file__))
SAVE = "/home/hatch/workspace/dojo-build/entry/renders"
os.makedirs(SAVE, exist_ok=True)
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=ROOT, **k)
    def do_POST(self):
        name = re.sub(r'[^a-z_]', '', self.path.split('name=')[-1]) + '.png'
        n = int(self.headers['Content-Length'])
        data = self.rfile.read(n)
        open(os.path.join(SAVE, name), 'wb').write(data)
        print("SAVED", name, len(data), flush=True)
        self.send_response(200); self.end_headers(); self.wfile.write(b'ok')
    def log_message(self, *a): pass
http.server.HTTPServer(('127.0.0.1', 8777), H).serve_forever()
