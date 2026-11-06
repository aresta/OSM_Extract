#!/bin/bash

# Generates a base outline map out of a PBF file, to be used as reference in
# the clip area web editor (scripts/clip_editor.py):
#   - coastlines
#   - administrative boundaries (country/regions/provinces as contour-like lines)
# The result is a small GeoJSON (maps/base_map.geojson) with 'natural' or
# 'boundary' properties to allow styling in the editor.
# It is always regenerated: no cache.

if [ $# -eq 0 ]; then
    echo "Usage:"
    echo "      $0 [input pbf file] [admin_levels, comma separated]"
    echo "      (defaults: /pbf/sp.pbf and 2,4,6: country + regions + provinces)"
    echo "Example: ./make_base_map.sh /pbf/sp.pbf"
    echo "         ./make_base_map.sh /pbf/sp.pbf 2,4,6,8"
    echo "Output: /maps/base_map.geojson"
    exit 1
fi

PBF="${1:-/pbf/sp.pbf}"
LEVELS="${2:-2,4,6}"          # country = 2, regions = 4, provinces = 6, counties = 8
OUT=/maps/base_map.geojson
TMP=/pbf/base_map_tmp
LEVELS_LIST=(${LEVELS//,/ })  # "2,4" -> list of levels
IN_LEVELS=$(printf "'%s'," "${LEVELS_LIST[@]}")
IN_LEVELS=${IN_LEVELS%,}      # admin_level sizes IN ('2','4')

rm -f "$OUT" "$TMP"  # ensure the GeoJSON driver does not try to overwrite

# --- boundaries: relations assembled as complete polygons/lines by gdal ------
ogr2ogr -f GeoJSON "$TMP" "$PBF" multipolygons \
    -where "boundary='administrative' AND admin_level IN ($IN_LEVELS)" 2>/dev/null
B_FEATURES=$(grep -c '"geometry"' "$TMP" || true)

# for small pbf extracts (cities), also keep the municipality borders
if [ "$B_FEATURES" -eq 0 ]; then
    echo "  No boundaries with admin_level $LEVELS, retrying with 2,4,6,8,10"
    LEVELS="2,4,6,8,10"
    LEVELS_LIST=(${LEVELS//,/ })
    IN_LEVELS=$(printf "'%s'," "${LEVELS_LIST[@]}")
    IN_LEVELS=${IN_LEVELS%,}
    rm -f "$TMP"
    ogr2ogr -f GeoJSON "$TMP" "$PBF" multipolygons \
        -where "boundary='administrative' AND admin_level IN ($IN_LEVELS)" 2>/dev/null
fi

mv "$TMP" /pbf/base_map_bound.geojson

# --- coastlines: fast osmium pre-filter (coastline ways are self tagged) -----
osmium tags-filter "$PBF" w/natural=coastline -o /pbf/base_map_coast.osm.pbf
ogr2ogr -f GeoJSON /pbf/base_map_coast_line.geojson /pbf/base_map_coast.osm.pbf lines

# --- merge both into a single compact file the editor serves -----------------
rm -f "$OUT"
python3 - <<'EOF'
import json
merged = {'type': 'FeatureCollection', 'features': []}
pairs = [('/pbf/base_map_bound.geojson', {'boundary': 'administrative'}),
         ('/pbf/base_map_coast_line.geojson', {'natural': 'coastline'})]
for file, prop in pairs:
    try:
        gj = json.load(open(file))
    except (FileNotFoundError, json.JSONDecodeError):
        continue
    for feat in gj.get('features', []):
        feat['properties'] = {**feat.get('properties', {}), **prop}
        merged['features'].append(feat)
json.dump(merged, open('/maps/base_map.geojson', 'w'), separators=(',', ':'))
EOF

rm -f /pbf/base_map_bound.geojson /pbf/base_map_coast.osm.pbf /pbf/base_map_coast_line.geojson

FEATURES=$(python3 -c "import json; print(len(json.load(open('$OUT')) ['features']))")
echo "Base map saved to: $OUT ($FEATURES features, admin_level: $LEVELS)"
