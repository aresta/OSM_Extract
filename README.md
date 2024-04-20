# OSM_Extract
Extract OSM vectorial map features in a configurable way to fmp files (text files with specific format) to be used by other projects.  For example, you can store the generated files in an SD card and use it to render maps.

This is intended to be used in projects with microcontrollers involving GPS location and display capabilities, with limited memory and speed. But it can be used in any project that needs to render simple vectorial maps.

Features:
- The area to be extracted can be configured in **/conf/clip_area.geojson** and **/scripts/pbf_to_geojson.sh**
- The features to be extracted can be configured in **/conf/conf_extract.yaml**
- The styles to apply to each feature type (color, width) can be configured in **conf_styles.yaml**

It produces binary files with the vectorial data of the features: lines and polygons, with the style information.

Each file contains the vectorial data of an area of approximately 4x4 Kms. Each folder contains 256 files (16x16 blocks), so it covers an approximate area of 64x64 Kms.  You can have as many folders as you need to cover your map area.

This is already used and working in the project: https://github.com/aresta/ESP32_GPS

Still work in progress.

Example of the creation of the map files:

First clip the pbf to your area:

```
/maps/osmium extract --strategy=smart -p ../conf/clip_area.geojson /pbf/spain-latest.osm.pbf -o /pbf/clipped.pbf
```

Then generate the intermediate lines and polygons files and the map files:
```
min_lon=123
min_lat=123
max_lon=123
max_lat=123

./pbf_to_geojson.sh $min_lon $min_lat $max_lon $max_lat /pbf/clipped.pbf /maps/test
echo "PBF extract done"

./extract_features.py $min_lon $min_lat $max_lon $max_lat /maps/test
echo "Map files created"
```

