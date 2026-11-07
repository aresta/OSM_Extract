# OSM_Extract
This tools are created to extract OpenStreetMap vectorial map features to *fmp* files (text with specific format) to be used by other projects to display custom maps with a subset of features and a custom styling.

For example, you can store the generated files in an SD card and use it to render maps in your custom device.

This is intended to be used in projects with microcontrollers involving GPS location and display capabilities. But it can be used in any project that needs to render simple vectorial maps.

## Example of the creation of the map files

### 1. Download the OpenStreetMap **PBF** file of your area

You can find them in [Geofabrik](https://download.geofabrik.de/) or https://download.openstreetmap.fr/extracts/

For example: *spain-latest.osm.pbf*
```bash
wget -P pbf -N http://download.openstreetmap.fr/extracts/europe/spain-latest.osm.pbf
```


### 2. Start docker

For the next steps you will need the docker container running:
```bash
docker compose up -d
```

### 3. Define your custom map area graphically

- First generate an outline map out of your PBF file (only once for a new pbf):

```bash
docker compose exec tools /scripts/make_base_map.sh /pbf/spain-latest.osm.pbf
```
It will generate a basic map with just coastlines, country, region and provinces boundaries, as a reference to draw your custom map boundaries.

- Then start the local app in docker to draw the **clip area** of your map graphically:
```bash
docker compose exec tools python3 /scripts/clip_editor.py
```
- Open **http://localhost:8080** in your browser and draw the polygon around the area you want for your map, or adjust it with the edit tool, and save. 

It writes */conf/clip_area.geojson*, used in the next steps to extract the map features of the defined area.


### 5. Features extraction and map files generation

```bash
docker compose exec tools /scripts/map_extraction.sh
```
Note: Some steps can throw *TopologyException* errors, because of some invalid geometries in the OSM pbf's. We can just ignore them.
- The feature types to be extracted can be configured in **/conf/conf_extract.yaml**
- The styles to apply to each feature type (color, width...) can be configured in **conf_styles.yaml**


The files in */maps* will contain the feature types defined in */conf/conf_extract.yaml* of your area, with the visual styles defined in */conf/conf_styles.yaml*


---
The map files are organized in a folder tree structure. Each folder contains several map files and has a custom name that defines the offset position of the map files in the folder.
- Each file contains the vectorial data of an area of approximately 4x4 Kms. 
- Each folder contains up to 256 files (16x16 blocks), so it covers an approximate area of 64x64 Kms.  
You can have as many folders as you need to cover your map area.

This is already used and working in the project: https://github.com/aresta/ESP32_GPS









