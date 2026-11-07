# Maps generation
- Processes to generate the custom map files for the GPS device:
    - Download OpenStreetMap pbf files for your area
    - Extract the needed features
    - Generate the custom map files to be used in the GPS device, via SD card.
- Uses docker with some tools like mapnik, osmium, gdal

## Config
```
  conf
    ├── clip_area.geojson       # defines the map area to clip from the pbf
    ├── conf_extract.yaml       # which features to extract from the pbf
    └── conf_styles.yaml        # defines how to render the map features: styles...
```

## Scripts
```
scripts
    ├── extract_features.py     # generate the compiled map files
    ├── funcs.py                # support functions
    ├── map_extraction.sh       # full pipeline: clip pbf -> geojson -> map files
```

check: README.md

## Editing the clip area graphically
- Generate the base outline map (coastlines + country/region/province boundaries) out of a pbf file: scripts/make_base_map.sh [pbf file] [admin levels: default 2,4,6]
- Start the editor server (inside docker): python3 /scripts/clip_editor.py -> http://localhost:8080
- Draw/adjust the polygon with the mouse and save: it writes conf/clip_area.geojson and shows the bbox to be used in the following scripts
