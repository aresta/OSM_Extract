#!/usr/bin/env python
import json
import os
import sys
from multiprocessing import Pool, cpu_count, Lock, Manager
from shapely.geometry import box
import yaml

# Import custom functionalities
from funcs import process_features_new, clip_lines, clip_polygons, style_features_new, render_map, lat2y, lon2x

# Constants
MAPBLOCK_SIZE_BITS = 12  # 4096 x 4096 coordinates per block
MAPFOLDER_SIZE_BITS = 4   # 16 x 16 blocks per folder
mapblock_mask = pow(2, MAPBLOCK_SIZE_BITS) - 1      # ...00000000111111111111
mapfolder_mask = pow(2, MAPFOLDER_SIZE_BITS) - 1    # ...00001111  
CONF_FEATURES = '../conf/conf_extract.yaml'
CONF_STYLES = '../conf/conf_styles.yaml'
MAP_FOLDER = '../maps/brazil'

lock = Lock()

def load_features(filepath):
    """Load GeoJSON features from a file."""
    with open(filepath, 'r') as file:
        return json.load(file)['features']

def write_polygon_feature(file, feature, min_x, min_y):
    """Write polygon features to the output file."""
    file.write(f"{feature['color']}\n")
    file.write(f"{feature['maxzoom']}\n")
    # bbox of the feature
    file.write(f"bbox:{int(round(feature['bbox'][0] - min_x))},{int(round(feature['bbox'][1] - min_y))},"
                f"{int(round(feature['bbox'][2] - min_x))},{int(round(feature['bbox'][3] - min_y))}\n")
    file.write("coords:")
    for coord in feature['geom'].exterior.coords:
        file.write(f"{int(round(coord[0] - min_x))},{int(round(coord[1] - min_y))};")
    file.write('\n')

def write_line_feature(file, feature, min_x, min_y):
    """Write line features to the output file."""
    file.write(f"{feature['color']}\n")
    file.write(f"{feature['width']}\n")
    file.write(f"{feature['maxzoom']}\n")
    # bbox of the feature
    file.write(f"bbox:{int(round(feature['bbox'][0] - min_x))},{int(round(feature['bbox'][1] - min_y))},"
                f"{int(round( feature['bbox'][2] - min_x))},{int(round( feature['bbox'][3] - min_y))}\n")

    file.write("coords:")
    for coord in feature['geom'].coords:
        file.write(f"{int(round(coord[0] - min_x))},{int(round(coord[1] - min_y))};")
    file.write('\n')

def handle_feature_processing(min_x, min_y, styled_polygons, styled_lines, styles, MAP_FOLDER, render_map_option):
    block_x = (min_x >> MAPBLOCK_SIZE_BITS) & mapfolder_mask
    block_y = (min_y >> MAPBLOCK_SIZE_BITS) & mapfolder_mask
    folder_name_x = min_x >> (MAPFOLDER_SIZE_BITS + MAPBLOCK_SIZE_BITS)
    folder_name_y = min_y >> (MAPFOLDER_SIZE_BITS + MAPBLOCK_SIZE_BITS)
    folder_name = f"{MAP_FOLDER}/{folder_name_x:+04d}{folder_name_y:+04d}"
    file_name = f"{folder_name}/{block_x}_{block_y}.fmp"
    
    os.makedirs(folder_name, exist_ok=True)
    image_folder = f"{MAP_FOLDER}/test_imgs"
    os.makedirs(image_folder, exist_ok=True)

    # Render optional map
    if render_map_option:
        image_path = f"{image_folder}/block_{folder_name_x}_{folder_name_y}-{block_x}_{block_y}.png"
        render_map(styled_polygons + styled_lines, image_path, min_x, min_y)

    # Export to .fmp file
    with open(file_name, "w", encoding='ascii') as file:
        file.write(f"Polygons:{len(styled_polygons)}\n")
        for polygon in styled_polygons:
            write_polygon_feature(file, polygon, min_x, min_y)
        file.write(f"Polylines:{len(styled_lines)}\n")
        for line in styled_lines:
            write_line_feature(file, line, min_x, min_y)

def process_block(args):
    """Processes a single map block."""
    global processed_counter, empty_counter  # Use the global counters
    min_x, min_y, styles, conf, lines, polygons, render_map_option, MAP_FOLDER, total_blocks, processed_counter, empty_counter = args
    mapblock_bbox = box(min_x, min_y, min_x + mapblock_mask, min_y + mapblock_mask + 1)
    styled_lines = list(clip_lines(style_features_new(lines, styles), mapblock_bbox))
    styled_polygons = list(clip_polygons(style_features_new(polygons, styles), mapblock_bbox))
    
    if styled_polygons or styled_lines:
        # Process blocks with features as usual
        handle_feature_processing(min_x, min_y, styled_polygons, styled_lines, styles, MAP_FOLDER, render_map_option)
        with lock:
            processed_counter.value += 1
    else:
        # Increment the empty block counter
        with lock:
            empty_counter.value += 1

    # Report progress including empty blocks
    with lock:
        total_processed = processed_counter.value + empty_counter.value
        percentage_complete = (total_processed / total_blocks) * 100
        print(f"Total processed: {total_processed}, Empty: {empty_counter.value}, Completion: {percentage_complete:.2f}%", end='\r')

def main():
    """Main function to orchestrate the processing."""
    if len(sys.argv) < 7:
        print("Usage: {} <min_lon> <min_lat> <max_lon> <max_lat> <geojson prefix name> <render_map (yes/no)>".format(sys.argv[0]))
        sys.exit(1)

    manager = Manager()
    processed_counter = manager.Value('i', 0)
    empty_counter = manager.Value('i', 0)

    min_lon, min_lat, max_lon, max_lat = map(float, sys.argv[1:5])
    geojson_prefix = sys.argv[5]
    render_map_option = sys.argv[6].lower() == 'yes'

    area_min_x, area_min_y = lon2x(min_lon), lat2y(min_lat)
    area_max_x, area_max_y = lon2x(max_lon), lat2y(max_lat)

    # Calculate the total number of tasks
    total_blocks = ((area_max_x - area_min_x) // 4096 + 1) * ((area_max_y - area_min_y) // 4096 + 1)

    conf = yaml.safe_load(open(CONF_FEATURES, "r"))
    styles = yaml.safe_load(open(CONF_STYLES, "r"))

    # Load and process all lines and polygons beforehand
    print(">>> Step 1/5 reading lines file")
    line_features = load_features(f"{MAP_FOLDER}/{geojson_prefix}_lines.geojson")

    print(">>> Step 2/5 reading polygons file")
    polygon_features = load_features(f"{MAP_FOLDER}/{geojson_prefix}_polygons.geojson")

    print(">>> Step 3/5 processing lines features")
    lines = list(process_features_new(line_features, conf['lines']))

    print(">>> Step 4/5 processing polygons features")
    polygons = list(process_features_new(polygon_features, conf['polygons']))

    print(">>> Step 5/5 styling and generating maps")
    tasks = [
        (
            init_x & (~mapblock_mask),
            init_y & (~mapblock_mask),
            styles, conf, lines, polygons, render_map_option, MAP_FOLDER, total_blocks, processed_counter, empty_counter
        )
        for init_x in range(area_min_x, area_max_x, 4096)
        for init_y in range(area_min_y, area_max_y, 4096)
    ]

    try:
        with Pool(processes=cpu_count()) as pool:
            pool.map(process_block, tasks)
        # Output final counters
        print(f"Final count: Total = {processed_counter.value + empty_counter.value} Processed = {processed_counter.value}, Empty = {empty_counter.value}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if pool:
            pool.terminate()  # Terminate the pool to stop all processes immediately
            pool.join()       # Wait for the processes to finish termination

if __name__ == "__main__":
    main()

