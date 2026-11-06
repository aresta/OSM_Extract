// Clip area editor: shows the base outline map extracted from the PBF
// (coastlines + admin boundaries) and lets you draw/edit the polygon to save
// into conf/clip_area.geojson (only a polygon, no tiles needed: fully offline).
// Interactions (draw/edit/drag/remove) are handled by leaflet-geoman-free.

var editLayer = new L.FeatureGroup(); // current clip polygon
var baseLayer = null;
var had_base  = false;
var had_clip  = false;
var fitted    = false;
var current   = null;   // featureCollection built from what's in editLayer

var CLIP_STYLE = { color:'#1a7ad4', weight:2, dashArray:'6 4', fillOpacity:0.10 };

function init_map(){
  var map = L.map('map', { zoomSnap:0.25 });
  map.setView([41, 2], 7);   // placeholder until the base map/clip area loads
  map.attributionControl.setPrefix('');
  map.attributionControl.addAttribution(
    'base map data &copy; OpenStreetMap contributors');

  map.addLayer(editLayer);

  map.pm.addControls({
    position: 'topright',
    drawPolygon: true, editMode: true, dragMode: true, removeMode: true,
    drawMarker: false, drawPolyline: false, drawCircle: false,
    drawCircleMarker: false, drawRectangle: false, drawText: false,
    cutPolygon: false, rotateMode: false
  });
  // zoom buttons under the geoman toolbar (the info box takes the top-left)
  map.removeControl(map.zoomControl);
  L.control.zoom({ position:'topright' }).addTo(map);

  map.pm.setGlobalOptions({ snapping: false, continueDrawing: false });

  map.on('pm:create', function(e){
    e.layer.setStyle(CLIP_STYLE);
    editLayer.addLayer(e.layer);
    // keep a single clip polygon: drop any older ones
    editLayer.eachLayer(function(layer){
      if (layer !== e.layer) editLayer.removeLayer(layer);
    });
    fitted = true; // the user navigated away: respect their view
    update_bbox();
  });
  // geoman fires pm:edit/pm:dragend on each layer, pm:create on the map
  map.on('pm:edit',    update_bbox);
  map.on('pm:dragend', update_bbox);
  map.on('pm:remove',  update_bbox);
  editLayer.on('layeradd', function(e){
    e.layer.on('pm:edit',    update_bbox);
    e.layer.on('pm:dragend', update_bbox);
    e.layer.on('pm:remove',  update_bbox);
  });

  return map;
}

function baseStyle(feat){
  var p = feat.properties || {}, t = p.tags || p;
  if (t.natural === 'coastline')
    return { color:'#2f7fa8', weight:2, opacity:0.9 };
  var level = String(p.admin_level != null ? p.admin_level : (t.admin_level || '4'));
  if (level === '2')   // country border: darker and thicker
    return { color:'#8f2f22', weight:2.4, opacity:0.95,
             fill:true, fillOpacity:0.02 };
  if (level === '6' || level === '7' || +level >= 8)  // provinces/counties: thin
    return { color:'#d0876c', weight:1, opacity:0.8,
             fill:true, fillOpacity:0.025, dashArray:'2 3' };
  // regions (admin_level 4) and any other lengths
  return { color:'#b04a3a', weight:1.3, opacity:0.85,
           fill:true, fillOpacity:0.035 };
}

function load_base_map(){
  return fetch('maps/base_map.geojson')
    .then(function(r){ return r.ok ? r.json() : null; })
    .then(function(gj){
      if (!gj) return;
      had_base = true;
      // canvas renderer: one bitmap for the thousands of paths (much faster
      // than ~5000 individual SVG nodes)
      var baseRenderer = L.canvas({ padding: 0.5 });
      baseLayer = new L.FeatureGroup();
      // build the vectors manually so each one is created with pmIgnore
      // (geoman checks the option at construction time only)
      for (var i = 0; i < gj.features.length; i++){
        var feat = gj.features[i];
        var opts = Object.assign({ pmIgnore:true, interactive:false,
                                   renderer: baseRenderer }, baseStyle(feat));
        var geomType = (feat.geometry || {}).type || '';
        var path = null;
        if (geomType == 'Polygon' || geomType == 'MultiPolygon'){
          // keep the nesting levels: multipolygon = [ [ ring, hole... ] ... ]
          var polys = geomType == 'MultiPolygon' ? feat.geometry.coordinates
                                                 : [feat.geometry.coordinates];
          path = L.polygon(
            polys.map(function(p){
              return p.map(function(r){
                return r.map(function(c){ return [c[1], c[0]]; });
              });
            }), opts);
        } else if (geomType == 'LineString' || geomType == 'MultiLineString'){
          var parts = geomType == 'MultiLineString' ? feat.geometry.coordinates
                                                    : [feat.geometry.coordinates];
          path = L.polyline(
            parts.map(function(p){
              return p.map(function(c){ return [c[1], c[0]]; });
            }), opts);
        } else continue;
        baseLayer.addLayer(path);
      }
      baseLayer.addTo(map);
      fit();
    });
}

function load_clip_area(){
  return fetch('conf/clip_area.geojson')
    .then(function(r){ return r.ok ? r.json() : null; })
    .then(function(gj){
      if (!gj) return;
      var feat = (gj.features || [])[0];
      if (!feat) return;
      var ring = feat.geometry.coordinates[0];
      var latlngs = ring.map(function(c){ return [c[1], c[0]]; });
      var poly = L.polygon(latlngs, CLIP_STYLE);
      editLayer.addLayer(poly);
      had_clip = true;
      fit();
      update_bbox();
    });
}

// fit the view once: to the clip area if any, else to the base outline
function fit(){
  if (fitted) return;
  if (had_clip && editLayer.getLayers().length){
    fitted = true;
    map.fitBounds(editLayer.getBounds(), { padding:[200,200] });
  } else if (had_base){
    fitted = true;
    map.fitBounds(baseLayer.getBounds(), { padding:[20,20] });
  }
}

function update_bbox(){
  // prune layers removed by geoman's removal mode
  editLayer.eachLayer(function(layer){
    if (!layer._map) editLayer.removeLayer(layer);
  });

  current = null;
  var layer = clip_polygon_layer();
  if (!layer) return;
  var ring = layer.toGeoJSON().geometry.coordinates[0];
  current = { type:'FeatureCollection', features: [
    { type:'Feature', properties:{},
      geometry:{ type:'Polygon', coordinates:[ ring ] } } ] };
}

function clip_polygon_layer(){
  var layers = editLayer.getLayers();
  for (var i = 0; i < layers.length; i++){
    var gj = layers[i].toGeoJSON && layers[i].toGeoJSON();
    if (gj && gj.geometry && gj.geometry.type === 'Polygon') return layers[i];
  }
  return null;
}

function save(){
  update_bbox();   // rebuild the polygon from the layers as they are right now
  if (!current){ status('Draw a polygon first'); return; }
  fetch('/save', { method:'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(current) })
    .then(function(r){ return r.json(); })
    .then(function(res){
      if (res.ok) status('saved: ' + res.file);
      else        status('error: ' + (res.error || 'unknown'));
    })
    .catch(function(e){ status('error: ' + e); });
}

function status(text){ document.getElementById('status').textContent = text; }

// activate the polygon tool by default, unless there is already a clip area
function start_drawing_if_empty(){
  if (!current) map.pm.enableDraw('Polygon');
}

var map = init_map();
document.getElementById('save').addEventListener('click', save);
update_bbox();
load_base_map();
load_clip_area().then(start_drawing_if_empty);
setInterval(fit, 1000); // retry until the view is fitted once
