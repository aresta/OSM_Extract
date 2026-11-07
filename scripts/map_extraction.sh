#!/bin/bash

CLIP_AREA=/conf/clip_area.geojson
MAP_PREFIX=/maps/map

# 1. Clip the raw pbf to the map area. 
echo -e "\nClipping PBF"
osmium extract --overwrite --strategy=smart -p $CLIP_AREA /pbf/spain-latest.osm.pbf -o /pbf/clipped.pbf

# 2. bbox: taken from the clip area: min_lon min_lat max_lon max_lat
IFS="," read -r min_lon min_lat max_lon max_lat < <(
  jq -r '.features[0].geometry.coordinates | add | [(map(.[0]) | min), (map(.[1]) | min), (map(.[0]) | max), (map(.[1]) | max)] | @csv' $CLIP_AREA
)
echo -e "bbox: $min_lon $min_lat $max_lon $max_lat\n"

# 3. Extract the features from the pbf to geojson: lines, polygons (WGS84 => Mercator EPSG:4326 => 3857)
rm -f ${MAP_PREFIX}_lines.geojson ${MAP_PREFIX}_polygons.geojson
ogr2ogr -t_srs EPSG:3857 -spat $min_lon $min_lat $max_lon $max_lat -clipsrc $CLIP_AREA ${MAP_PREFIX}_lines.geojson /pbf/clipped.pbf lines
ogr2ogr -t_srs EPSG:3857 -spat $min_lon $min_lat $max_lon $max_lat -clipsrc $CLIP_AREA ${MAP_PREFIX}_polygons.geojson /pbf/clipped.pbf multipolygons
echo -e "PBF extract done\n"

# 4. Build the map files
rm -rf /maps/mymap
/scripts/extract_features.py $min_lon $min_lat $max_lon $max_lat $MAP_PREFIX
echo -e "Map files created\n"
echo -e "Done!\n"
