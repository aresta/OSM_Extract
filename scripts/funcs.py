from shapely import geometry, LineString, LinearRing, Polygon, MultiPolygon, MultiLineString, Point, intersection
from shapely.geometry import shape
from shapely.ops import triangulate
import PIL.ImageDraw as ImageDraw
import PIL.Image as Image
import math

IMG_WIDTH, IMG_HEIGHT = pow( 2, 12), pow( 2, 12) # 4096 x 4096
BACKGROUND_COLOR = 0xDDDDDD

PI = math.pi
def DEG2RAD(a): return ((a) / (180 / PI))
def RAD2DEG(a): return ((a) * (180 / PI))
EARTH_RADIUS = 6378137
def lat2y( lat): return round( math.log( math.tan( DEG2RAD(lat) / 2 + PI/4 )) * EARTH_RADIUS)
def lon2x( lon): return round( DEG2RAD(lon) * EARTH_RADIUS)

def parse_tags(tags_str):
    """ Extract the tags as dict
    """
    res = dict()
    tags = tags_str.split('","')
    for tag in tags:
        tag = tag.replace('"','')
        parts = tag.split('=>')
        res[parts[0]] = parts[1]
    return res

def get_geoms( osm_geom ):
    """ Converts the geometry or multigeometry to a list of simple geometries (LineString, Polygon)
    """
    geoms = []
    geom_type = osm_geom['type']
    if geom_type == 'LineString':
        geoms.append( LineString( osm_geom['coordinates']))
    elif geom_type == 'Polygon':
        geoms.append( Polygon( osm_geom['coordinates']))
    elif geom_type == 'MultiLineString':
        for g in osm_geom['coordinates']:
            geoms.append( LineString( g))
    elif geom_type == 'MultiPolygon':
        # print("g", osm_geoms)
        geoms.append( Polygon( osm_geom['coordinates'][0][0])) # we take just the 1st, the rest are holes #TODO: manage holes
    else: print("ERROR. Unknow osm geom type:", geom_type)
    # elif geom_type == 'GeometryCollection': # TODO
    #     return []    
    # else: print("ERROR: unknow geometry type:", geom_type)
    return geoms

def process_features_new(features, conf):
    done = 0
    feat_found = set()

    for feature in features:
        properties = feature['properties']
        if 'other_tags' in properties:
            tags = parse_tags(properties['other_tags'])
        else:
            tags = dict()
        
        if 'tags' in conf:
            for tag in conf['tags']:
                if tag in tags:
                    properties[tag] = tags[tag]

        feature_type = None
        feature_type_tags = []
        z_order = properties.get('z_order', None)
        
        for conf_feat_type in conf['feature_types']:
            if conf_feat_type in properties:
                feat_subtype = properties[conf_feat_type]
                filter_by_subtype = len(conf['feature_types'][conf_feat_type]) > 0
                if filter_by_subtype and feat_subtype not in conf['feature_types'][conf_feat_type]:
                    continue
                feature_type = conf_feat_type + '.' + feat_subtype
                if isinstance(conf['feature_types'][conf_feat_type], list):
                    break  # No tags to check, we are done
                conf_feature_tags = conf['feature_types'][conf_feat_type][feat_subtype]
                for feat_subtype_tag in conf_feature_tags:
                    if feat_subtype_tag in tags:
                        feature_type_tags.append(feat_subtype_tag + '.' + tags[feat_subtype_tag])
                break

        if not feature_type:
            done += 1
            continue

        geom = shape(feature['geometry'])  # Convert geometry from GeoJSON to Shapely object
        if not geom.is_valid or geom.is_empty:
            done += 1
            continue

        geom_type = 'line' if geom.geom_type in ('LineString', 'MultiLineString') else 'polygon'
        feat_found.add(feature_type)  # Collect unique feature types

        # Yielding each feature as soon as it's processed
        yield {
            'id': properties.get('osm_way_id', properties.get('osm_id', '')),
            'type': feature_type,
            'geom_type': geom_type,
            'tags': feature_type_tags,
            'z_order': z_order,
            'geom': geom
        }
        done += 1
#        print("... Extraction completed with {} features".format(done), end='\r')

#    print("\n... Feature types extracted: [{}]".format(", ".join(sorted(feat_found))))


def process_features(features, conf):
    extracted = []
    done = 0
    feat_found = set()

    for feature in features:
        properties = feature['properties']
        if 'other_tags' in properties:
            tags = parse_tags(properties['other_tags'])
        else:
            tags = dict()
        
        if 'tags' in conf:
            for tag in conf['tags']:
                if tag in tags:
                    properties[tag] = tags[tag]

        feature_type = None
        feature_type_tags = []
        z_order = properties.get('z_order', None)
        
        for conf_feat_type in conf['feature_types']:
            if conf_feat_type in properties:
                feat_subtype = properties[conf_feat_type]
                filter_by_subtype = len(conf['feature_types'][conf_feat_type]) > 0
                if filter_by_subtype and feat_subtype not in conf['feature_types'][conf_feat_type]:
                    continue
                feature_type = conf_feat_type + '.' + feat_subtype
                if isinstance(conf['feature_types'][conf_feat_type], list):
                    break  # No tags to check, we are done
                conf_feature_tags = conf['feature_types'][conf_feat_type][feat_subtype]
                for feat_subtype_tag in conf_feature_tags:
                    if feat_subtype_tag in tags:
                        feature_type_tags.append(feat_subtype_tag + '.' + tags[feat_subtype_tag])
                break

        if not feature_type:
            done += 1
            continue

        geom = shape(feature['geometry'])  # Convert geometry from GeoJSON to Shapely object
        if not geom.is_valid or geom.is_empty:
            done += 1
            continue

        geom_type = 'line' if geom.geom_type in ('LineString', 'MultiLineString') else 'polygon'

        extracted.append({
            'id': properties.get('osm_way_id', properties.get('osm_id', '')),
            'type': feature_type,
            'geom_type': geom_type,
            'tags': feature_type_tags,
            'z_order': z_order,
            'geom': geom
        })
        feat_found.add(feature_type)  # Collect unique feature types
        done += 1
        print("... Extraction completed with {} features".format(done), end='\r')

    print("\n... Feature types extracted: [{}]".format(", ".join(sorted(feat_found))))

    return extracted

def style_features_new(features, styles):
    """
    Apply styles (color, width) to the features based on the definitions in styles.
    This function now uses a generator to yield styled features one at a time.
    """
    for feat in features:
        feature_type = feat['type']
        feature_type_group = feature_type.split('.')[0]
        feature_color = '0xF972'  # default pink
        feature_width = None  # default
        feature_maxzoom = ''  # default
        found = False
        conf_styles = styles['lines'] if feat['geom_type'] == 'line' else styles['polygons']
        for style_item in conf_styles:
            if feature_type in style_item['features'] or feature_type_group in style_item['features']:
                if 'color' in style_item: feature_color = styles["colors"][style_item['color']]
                if 'width' in style_item: feature_width = style_item['width']
                if 'maxzoom' in style_item: feature_maxzoom = style_item['maxzoom']
                found = True
                break  # keep first match
        if not found: 
            print("Not mapped: ", feature_type, feature_type_group)
        
        styled_feature = {
            'id': feat['id'],  # for debugging
            'type': feature_type,  # retain for further processing if necessary
            'geom_type': feat['geom_type'],
            'color': feature_color, 
            'width': feature_width,
            'maxzoom': feature_maxzoom,
            'z_order': feat.get('z_order', 0),  # Default z_order to 0 if not provided
            'geom': feat['geom']
        }
        yield styled_feature


def style_features( features, styles):
    """Apply styles (color,width) to the features based in the definitions in styles
    """
    styled_features = []
    for feat in features:
        feature_type = feat['type']
        feature_type_group = feat['type'].split('.')[0]
        feature_color = '0xF972' # default pink
        feature_width = None   # default
        feature_maxzoom = ''   # default
        found = False
        conf_styles = styles['lines'] if feat['geom_type'] == 'line' else styles['polygons']
        for style_item in conf_styles:
            if feature_type in style_item['features'] or feature_type_group in style_item['features']:
                if 'color' in style_item: feature_color = styles["colors"][ style_item['color']]
                if 'width' in style_item: feature_width = style_item['width']
                if 'maxzoom' in style_item: feature_maxzoom = style_item['maxzoom']
                found = True
                break # keep first match
        if not found: 
            print("Not mapped: ", feature_type, feature_type_group)
        styled_features.append({
            'id': feat['id'],  # for debugging
            'type': feature_type, # remove
            'geom_type': feat['geom_type'],
            'color': feature_color, 
            'width': feature_width,
            'maxzoom': feature_maxzoom,
            'z_order': feat['z_order'],
            'geom': feat['geom'],
            })
    return styled_features

# Modifying the clipping functions to use generators
# These changes make the clipping operations yield features one at a time instead of building a list in memory.
def clip_lines(features, bbox):
    """ Clip lines to the box area. Each line can be split into one or several lines.
    """
    for feat in features:
        line = feat['geom']
        if bbox.intersects(line):
            parts = line.intersection(bbox)
            if isinstance(parts, LineString):
                parts = [parts]
            elif isinstance(parts, MultiLineString):
                parts = list(parts.geoms)
            else:
                continue

            for part in parts:
                if part.is_valid and not part.is_empty:
                    new_feat = dict(feat)
                    new_feat['geom'] = part
                    new_feat['bbox'] = part.bounds
                    yield new_feat

def clip_polygons(features, bbox):
    """ Clip polygons to the bbox area. Each polygon can be split into one or several polygons.
    """
    for feat in features:
        polygon = feat['geom']
        if bbox.intersects(polygon):
            parts = polygon.intersection(bbox)
            if isinstance(parts, Polygon):
                parts = [parts]
            elif isinstance(parts, MultiPolygon):
                parts = list(parts.geoms)
            else:
                continue

            for part in parts:
                if part.is_valid and not part.is_empty:
                    new_feat = dict(feat)
                    new_feat['geom'] = part
                    new_feat['bbox'] = part.bounds
                    yield new_feat

def color_to_24bits( color565):
    """ Convert color codification. 
        Some displays use RGB565 schema: 5 bits, 6 bits, 5 bits.
    """
    color565 = int( color565, 16) # convert from hex string
    r = (color565 >> 8) & 0xF8
    r |= (r >> 5)
    g = (color565 >> 3) & 0xFC
    g |= (g >> 6)
    b = (color565 << 3) & 0xF8
    b |= (b >> 5)
    return (b << 16) | (g << 8) | r  # for some reason it expects the channels in reverse order (bgr)


def draw_feature( draw: ImageDraw, feat, min_x, min_y ):
    coords = feat['geom'].exterior.coords if type( feat['geom']) == Polygon else feat['geom'].coords
    points = [ (( x-min_x), IMG_HEIGHT-(y-min_y) ) for x,y in coords]
    color = color_to_24bits( feat['color'])    
    if feat['geom_type'] == 'polygon':
        draw.polygon( points, fill = color)
    else:
        width = max( round( feat['width']), 1) if feat['width'] else 1
        draw.line( points, fill = color, width = width)

def render_map( features, file_name, min_x, min_y):
    """Export an image of the features
    """
    image = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), color=BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)
    for feat in features:
        draw_feature( draw, feat, min_x=min_x, min_y=min_y)
    image.save( file_name)
