# OSM_Extract
This tools are created to extract OpenStreetMap vectorial map features in a configurable way to fmp files (text files with specific format) to be used by other projects to display custom maps with a subset of map features and a custom styling.

For example, you can store the generated files in an SD card and use it to render maps in your custom device.

This is intended to be used in projects with microcontrollers involving GPS location and display capabilities. But it can be used in any project that needs to render simple vectorial maps.

Features:
- The area to be extracted can be configured in **/conf/clip_area.geojson**. 

- The script **/scripts/pbf_to_geojson.sh** is used to do the extraction.

- The feature types to be extracted can be configured in **/conf/conf_extract.yaml**

- The styles to apply to each feature type (color, width...) can be configured in **conf_styles.yaml**

It produces custom text files with the vectorial data of the features: lines and polygons, with the style information.

The map files are organized in a folders structure. Each folder contains several map files and has a custom name that defines the offset position of the map files in the folder.

Each file contains the vectorial data of an area of approximately 4x4 Kms. 

Each folder contains up to 256 files (16x16 blocks), so it covers an approximate area of 64x64 Kms.  You can have as many folders as you need to cover your map area.

This is already used and working in the project: https://github.com/aresta/ESP32_GPS

Still work in progress.

## Example of the creation of the map files

1. Download the OpenStreetMap **PBF** file of your ares with all the map features.  You can find them in [Geofabrik](https://download.geofabrik.de/) or https://download.openstreetmap.fr/extracts/

For example: *spain-latest.osm.pbf*


2. Clip the pbf to your area:

```
/maps/osmium extract --strategy=smart -p ../conf/clip_area.geojson /pbf/spain-latest.osm.pbf -o /pbf/clipped.pbf
```
It will generate an smaller PBF file of a reduced area, defined by the clipping square in *clip_area.geojson*


3. Then generate the intermediate lines and polygons files and the map files:
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
It will extract and generate the compiled map files in the folder */maps/test/* 

These files will contain the feature types defined in */conf/conf_extract.yaml* of your area, with the visual styles defined in */conf/conf_styles.yaml*

