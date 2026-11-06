#!/usr/bin/env python3
# Small web server to edit the clipping area (conf/clip_area.geojson) graphically.
# Run it inside the docker container: python3 /scripts/clip_editor.py
# Then open: http://localhost:8080

import json, os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

WEB_DIR   = '/scripts/web'
CONF_DIR  = '/conf'
MAPS_DIR  = '/maps'
CLIP_FILE = os.path.join(CONF_DIR, 'clip_area.geojson')
PORT      = 8080


def in_dir(path, root):
    """ prevent escaping out of the served directories """
    root = os.path.realpath(root)
    return os.path.realpath(path) == root or os.path.realpath(path).startswith(root + os.sep)


class Handler(SimpleHTTPRequestHandler):

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')  # always fresh JS/styles
        SimpleHTTPRequestHandler.end_headers(self)

    def translate_path(self, path):
        """ serve /maps/... and /conf/... from their real folders, the rest from WEB_DIR """
        path = path.split('?', 1)[0].split('#', 1)[0]
        if path.startswith('/maps/'):
            f = os.path.join(MAPS_DIR, path[len('/maps/'):])
            if in_dir(f, MAPS_DIR): return f
        elif path.startswith('/conf/'):
            f = os.path.join(CONF_DIR, path[len('/conf/'):])
            if in_dir(f, CONF_DIR): return f
        return os.path.join(WEB_DIR, path[1:] or 'index.html')

    def do_POST(self):
        if not self.path.startswith('/save'):
            self.send_error(404); return
        try:
            length = int(self.headers.get('Content-Length', 0))
            data = json.loads(self.rfile.read(length))
            bbox = self.save_clip_area(data)
        except Exception as e:
            self.send_json_response(400, {'ok': False, 'error': str(e)}); return
        self.send_json_response(200, {'ok': True, 'bbox': bbox,
                                      'file': CLIP_FILE})

    def send_json_response(self, code, obj):
        body = json.dumps(obj).encode('ascii')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def save_clip_area(self, data):
        """ validate the polygon received and write it to the clipping config file """
        if data.get('type') != 'FeatureCollection' or not data.get('features'):
            raise ValueError("A FeatureCollection with one polygon is expected")
        feature = data['features'][0]
        geom = feature.get('geometry') or {}
        if geom.get('type') != 'Polygon' or not geom.get('coordinates'):
            raise ValueError("The feature must be a Polygon")
        ring = geom['coordinates'][0]  # outer ring: [[lon, lat], ...]
        if len(ring) < 4:
            raise ValueError("The polygon needs at least 3 points")
        for pos in ring:
            lon, lat = pos[0], pos[1]
            if not (-180 < lon < 180 and -85 < lat < 85):
                raise ValueError("Coordinate out of range: %s" % (pos,))
        if ring[0] != ring[-1]:        # force the closing point
            ring.append(list(ring[0]))

        geojson = {'type': 'FeatureCollection', 'features': [{
                       'type': 'Feature', 'properties': {},
                       'geometry': {'coordinates': [ring], 'type': 'Polygon'}}]}
        with open(CLIP_FILE, 'w') as file:
            json.dump(geojson, file, indent=2)

        xs = [pos[0] for pos in ring]; ys = [pos[1] for pos in ring]
        return [min(xs), min(ys), max(xs), max(ys)]

    def log_message(self, fmt, *args):
        print("  %s" % (fmt % args))


if __name__ == '__main__':
    print("\n  Clip area editor: open http://localhost:%d in your browser" % PORT)
    print("  (C-c to quit)\n")
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
