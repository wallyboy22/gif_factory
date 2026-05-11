var bioms = ee.FeatureCollection('projects/mapbiomas-workspace/AUXILIAR/biomas-2019').filterMetadata('CD_Bioma', 'equals', 3);
Map.addLayer(bioms)

// get protected areas
var pa = ee.FeatureCollection('projects/mapbiomas-workspace/AUXILIAR/areas-protegidas')
    .filterMetadata('name', 'equals', 'PARNA da Chapada dos Veadeiros')

var pa = bioms;


var matopiba = ee.FeatureCollection('users/dh-conciani/vectors/matopiba_lapig_cerrado');


var col7 = ee.Image('projects/mapbiomas-workspace/public/collection7/mapbiomas_collection70_integration_v2')
    .select(['classification_1985'])
    .clip(geometry);

// ler recorte de biomas
var biomes = ee.Image('projects/mapbiomas-workspace/AUXILIAR/biomas-2019-raster');

// REMAPEAR 
// NATURAL = 1
// ANTRÓPICO = 2

// ler coleção 7
var col = ee.Image('projects/mapbiomas-workspace/public/collection7/mapbiomas_collection70_integration_v2')
    .select(['classification_2021'])
    .remap([1, 3, 4, 5, 10, 11, 12, 32, 29, 13, 14, 15, 18, 19, 39, 20, 40, 41, 36, 46, 47, 48, 9, 21, 22, 23, 24, 30, 25, 26, 33, 31, 27],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0]);

// ler coleção sentinel 
var sen = ee.ImageCollection('projects/mapbiomas-workspace/COLECAO7-S2/integracao')
    .filter(ee.Filter.eq('version', '0-1'))
    .mosaic()
    .select(['classification_2021'])
    .remap([1, 3, 4, 5, 10, 11, 12, 32, 29, 13, 14, 15, 18, 19, 39, 20, 40, 41, 36, 46, 47, 48, 9, 21, 22, 23, 24, 30, 25, 26, 33, 31, 27],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0]);


// calcular concordância
var conc = ee.Image(0).where(sen.eq(1).and(col.eq(1)), 1)   // [1]: Concordância
    .where(sen.eq(1).and(col.neq(1)), 2)        // [2]: Apenas Sentinel
    .where(sen.neq(1).and(col.eq(1)), 3)        // [3]: Apenas Landsat
    .selfMask()
    .updateMask(biomes.eq(4))
    .rename('agreement');

// get land tenure
var tenure = ee.Image('users/mapbiomascerrado1/fundiarioN3');

// remap
tenure = tenure.remap([0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [6, 3, 4, 8, 8, 2, 5, 1, 7, 8]);

// 1: Imóvel rural privado
// 2: Assentamento rural
// 3: Terra Índigena
// 4: UC
// 5: APA
// 6: Sem info. cadastral
// 7: Florestas públicas não destinadas
// 8: Outros

// map 1
tenure = tenure.updateMask(tenure.eq(1))
    .blend(tenure.updateMask(tenure.eq(2)))
//.blend(tenure.updateMask(tenure.eq(5)));


//Map.addLayer(col7, vis, 'col7')


var biomes = ee.Image('projects/mapbiomas-workspace/AUXILIAR/biomas-2019-raster');

var br_states = ee.Image('projects/mapbiomas-workspace/AUXILIAR/estados-2016-raster')
    .updateMask(biomes.eq(4));
//br_states = br_states.updateMask(br_states.eq(51));

// get collection
var col = ee.Image('projects/mapbiomas-workspace/FOGO_COL2/SUBPRODUTOS/mapbiomas-fire-collection2-fire-frequency-v1')
    .select('fire_frequency_1985_2022')
    .divide(100).int()
    .updateMask(br_states);

// remap years
var recipe = ee.Image([]);
ee.List.sequence({ 'start': 1985, 'end': 2021 }).getInfo()
    .forEach(function (year_i) {
        // get year i
        var x = col.select(['classification_' + year_i])
            .remap([11, 0],
                [11, 0])
            .rename('classification_' + year_i);
        // bind
        recipe = recipe.addBands(x);
    });


var fundo = ee.Image(1).visualize({ palette: 'white' })


var vec_estados = ee.FeatureCollection('projects/mapbiomas-workspace/AUXILIAR/estados-2016')
//.filterBounds(bioms);

var vec_estados2 = ee.Image().paint(vec_estados, 'vazio', 3).visualize({ palette: 'black' })




var cerrado = ee.Image().paint(bioms).visualize({ palette: 'fcfcfc' })
//.paint(featureCollection, color, width) 

var cerrado_line = ee.Image().paint(bioms, 'vazio', 3).visualize({ palette: '#403D3D' })

var biom = ee.FeatureCollection('projects/mapbiomas-workspace/AUXILIAR/biomas-2019')
var biomes_line = ee.Image().paint(biom, 'vazio', 3).visualize({ palette: '#403D3D' })




var style = require('users/gena/packages:style');
var textProperties = { fontSize: 14, textColor: '000000', outlineColor: 'ffffff', outlineWidth: 2, outlineOpacity: 0.6 };

var scale = style.ScaleBar.draw(geometryScaleBar, {
    steps: 3, palette: ['000000', 'fefefe'], multiplier: 1000, format: '%.0f', units: 'km', text: textProperties
});


// get brtzil
var brazil = ee.FeatureCollection('projects/mapbiomas-workspace/AUXILIAR/brasil_2km')
var brazil_line = ee.Image().paint(brazil, 'vazio', 3).visualize({ palette: '#BABABA' });

var biomas = ee.FeatureCollection('projects/mapbiomas-workspace/AUXILIAR/biomas-2019');
var biomas_line = ee.Image().paint(biomas, 'vazio', 3).visualize({ palette: 'black' });



//Map.addLayer(def_by_period2, {palette: ['#E9E9E9', '#FEF5CD', '#F5BA0D', '#F50909', '#003AFF'], min: 0, max: 4}, 'Def');


//Map.addLayer(def_by_period, {palette: ['#DDDAD9', '#F6F321', '#F50909', '#FF00F7'], min: 1985, max: 2021}, 'Def');

//print(recipe)
//Map.addLayer(recipe.select(0).randomVisualizer())

// fire regime change
var fire_regime_change = ee.Image('projects/mapbiomas-workspace/DEGRADACAO/FOGO/fire_regime_changes_v2')
//.updateMask(biomes.eq(4));

// structure change
var structure = ee.Image('projects/mapbiomas-workspace/DEGRADACAO/TRAJECTORIES/COL71/STRUCTURAL_CHANGE_V5')
    .select('structure_change')
//.updateMask(biomes.eq(4));
//.remap([4,5],[0,1]);

var direction = ee.Image('projects/mapbiomas-workspace/DEGRADACAO/TRAJECTORIES/COL71/STRUCTURAL_CHANGE_V5')
    .select('direction')
//.updateMask(biomes.eq(4));


// Get tracks
// Paint the lines onto the empty image
var veadeiros = ee.Image().byte().paint({
    featureCollection: ee.FeatureCollection('users/dh-conciani/basemaps/field-track/VEADEIROS_TERRA_RONCA_MAR_2022'),
    color: 1,  // Color to paint the lines (could be an integer or a color code)
    width: 6   // Width of the lines in pixels
});

var veadeiros2 = ee.Image().byte().paint({
    featureCollection: ee.FeatureCollection('users/dh-conciani/basemaps/field-track/VEADEIROS_SET_2022'),
    color: 2,  // Color to paint the lines (could be an integer or a color code)
    width: 6   // Width of the lines in pixels
});

var matopiba = ee.Image().byte().paint({
    featureCollection: ee.FeatureCollection('users/dh-conciani/basemaps/field-track/MATOPIBA_MAR_2023'),
    color: 3,  // Color to paint the lines (could be an integer or a color code)
    width: 6   // Width of the lines in pixels
});

var araguaia = ee.Image().byte().paint({
    featureCollection: ee.FeatureCollection('users/dh-conciani/basemaps/field-track/ARAGUAIA_JUN_2023'),
    color: 4,  // Color to paint the lines (could be an integer or a color code)
    width: 6   // Width of the lines in pixels
});

// bind
var routes = veadeiros.blend(veadeiros2).blend(matopiba).blend(araguaia);



// plot maps

var mosaic = ee.ImageCollection('projects/nexgenmap/MapBiomas2/SENTINEL/mosaics-3')
    .filterMetadata('year', 'equals', 2022)
    .filterMetadata('version', 'equals', '3')
    .filterMetadata('biome', 'equals', 'CERRADO')
    .mosaic()
    .clip(bioms);

// carregar stable 
var stable = ee.Image('users/dh-conciani/basemaps/stable_col8_level0')
    .remap([0, 1, 14],
        [1, 2, 3]);


// import the color ramp module from mapbiomas 
var palettes = require('users/mapbiomas/modules:Palettes.js');
var vis = {
    'min': 0,
    'max': 62,
    'palette': palettes.get('classification8')
};

// deforestation
var def = ee.Image('users/dh-conciani/basemaps/deforestation_byPeriod_col8');

// collection 8
var col8 = ee.Image('projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1')
    .select('classification_2023');

// REMAP TO LEVEL 0N1
var remap = col8.remap({
    'from': [3, 5, 6, 49],
    'to': [3, 3, 3, 3],
    'defaultValue': 0
}).selfMask()

print(remap)

// foca mean terrain
var focal = ee.Image('users/dh-conciani/basemaps/focalDiff_cerrado_500m');

//Map.addLayer(focalMax, {palette: ['green', 'yellow', 'red'], min:0, max:1500}, 'Max', false);
//Map.addLayer(focalMin, {palette: ['green', 'yellow', 'red'], min:0, max:1500}, 'Min', false);
//Map.addLayer(focalDiff, {palette: ['green', 'yellow', 'red'], min:0, max:100}, 'Diff', true);
//Map.addLayer(slope, {palette: ['green', 'yellow', 'red'], min:0, max:10}, 'Slope', false);


/**
 * Generates a hex grid with a unique ID in each grid cell and calculates carbon stock per unit area.
 * 
 * Args:
 *    proj: Projection to use
 *    diameter: size of each hexagon from edge to edge in projection units.
 *    carbonStock: Image containing the carbon stock data per pixel
 * Returns an image containing unique IDs in a hexagonal grid pattern and carbon stock per unit area.
 * 
 * Based on http://playtechs.blogspot.com/2007/04/hex-grids.html
 * Development: Instituto de Pesquisa Ambiental da Amazônia - IPAM
 * contact: barbara.silva@ipam.org.br
 * 
 */

// --- --- --- HexGrid function
var hexGridWithCarbon = function (proj, diameter, carbonStock) {
    var size = ee.Number(diameter).divide(Math.sqrt(3)); // Distance from center to vertex
    var areaPerHex = Math.pow((diameter / 2) / 1000, 2) * Math.sqrt(3) / 2; // Area in km^2

    var coords = ee.Image.pixelCoordinates(proj);
    var vals = {
        // Switch x and y here to get flat top instead of pointy top hexagons.
        x: coords.select("x"),
        u: coords.select("x").divide(diameter),  // term 1
        v: coords.select("y").divide(size),      // term 2
        r: ee.Number(diameter).divide(2),
    };
    var i = ee.Image().expression("floor((floor(u - v) + floor(x / r))/3)", vals);
    var j = ee.Image().expression("floor((floor(u + v) + floor(v - u))/3)", vals);

    // Turn the hex coordinates into a single "ID" number.
    var cells = i.long().leftShift(32).add(j.long()).rename("hexgrid");

    // Calculate carbon stock per unit area for each hexagon.
    var carbonPerArea = carbonStock.divide(areaPerHex).rename("carbon_per_area");

    return cells.addBands(carbonPerArea);
};

// Define a region for masking hexagons.
var region = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017')
    .filter("country_na == 'Brazil'")
    .union()
    .first()
    .geometry();

// Import edge area asset
var data = ee.Image('projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/summary/edge_v3');

// get 2022 
var first = data.select('edge_1985');
first = first.updateMask(first.lte(90));

var last = data.select('edge_2022');
last = last.updateMask(last.lte(90));

// Generate a hex cogrid with carbon stock per unit area and mask off cells that don't touch the region.
var gridFirst = hexGridWithCarbon(ee.Projection('EPSG:4674'), 0.5, first);
var regionImg = ee.Image(0).byte().paint(region, 1);
var mask = gridFirst.select("hexgrid").addBands(regionImg)
    .reduceConnectedComponents(ee.Reducer.sum(), "hexgrid", 256);

gridFirst = gridFirst.updateMask(mask);

// Calculate mean carbon stock per unit area per hexagon.
var sumFirst = gridFirst.reduceConnectedComponents(ee.Reducer.sum(), "hexgrid", 256);

var gridLast = hexGridWithCarbon(ee.Projection('EPSG:4674'), 0.5, last);
var regionImg = ee.Image(0).byte().paint(region, 1);
var mask = gridLast.select("hexgrid").addBands(regionImg)
    .reduceConnectedComponents(ee.Reducer.sum(), "hexgrid", 256);

gridLast = gridLast.updateMask(mask);
// Calculate mean carbon stock per unit area per hexagon.
var sumLast = gridLast.reduceConnectedComponents(ee.Reducer.sum(), "hexgrid", 256);

// Define visualization properties.
/*
var vis = {
  min: 1e1, // soma dos estoques de COS
  max: 20000000000,
  palette: ["001219","005f73","0a9396","94d2bd","e9d8a6","ee9b00","ca6702","bb3e03","ae2012","9b2226"]
};
*/

// Make a visualization composite.
var background = ee.Image(0).visualize({ palette: '000000' });
var carbonVis = sumFirst.select('carbon_per_area').visualize({
    palette: vis.palette,
    min: vis.min,
    max: vis.max,
    opacity: 0.6
});
var composite = background.blend(carbonVis).blend(sumFirst.visualize(vis));
var composite2 = background.blend(carbonVis).blend(sumLast.visualize(vis));

// Display the results on the map.



var ref = ee.Image('projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/native_mask/nativeMask_col101_v2')

Map.addLayer(ref.select('classification_2023'), { palette: ['gray'], min: 1, max: 100 }, 'ref')



/// 
////////////// edge size ************
// list years to be processed
var years = [1985, 1986, 1987, 1988, 1989, 1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997,
    1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
    2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023];

// set classes to be processed
var classList = [3, 5, 6, 49];

var edge_asset = 'projects/mapbiomas-brazil/assets/DEGRADATION/COLLECTION-10/public/degradation_edge_area_col101_v2';
var edge_sizes = [300, 150, 120, 90, 60, 30];

var edge_age = 'projects/mapbiomas-brazil/assets/DEGRADATION/COLLECTION-10/public/degradation_edge_age_col101_v2'

//Map.addLayer(
//  ee.Image(edge_asset).select('edge_2023')
//  .updateMask(ee.Image(edge_asset).select('edge_2023')
//  .lte(150)), 
//  {palette:['#FF0001','#32CD32','#19B06F','#6FA8DC','#0B5394','#A64D79'], min:30, max: 150},
//  'Edge')

Map.addLayer(ee.Image(edge_asset).select('edge_2023')
    .updateMask(ee.Image(edge_asset).select('edge_2023')
        .lte(150)),
    { palette: ['red', '#00BFC4', '#00BFC4', '#00BFC4', '#00BFC4', '#00BFC4'], min: 30, max: 150 },
    'Edge')

var x = ee.Image(edge_asset).select('edge_2023').lte(150).selfMask()
    .updateMask(ee.Image(edge_age).select('age_2023').gte(10).selfMask())

var y = ee.Image(edge_age).select('age_2023')
    .updateMask(ee.Image(edge_asset).select('edge_2023').lte(30).selfMask())

//Map.addLayer(y, {palette:["#228B22", "#2F9420", "#3C9D1F", "#49A61D", "#56AF1C",
//                  "#63B81A", "#70C119", "#7DCA17", "#8AD316", "#97DC14",
//                "#A4E513", "#B1EE11", "#BEF710", "#CCFF0E", "#D8F20D",
//                "#E4E50C", "#F0D80B", "#FCCC0A", "#FFBE09", "#FFB108",
//                "#FFA307", "#FF9606", "#FF8905", "#FF7B04", "#FF6E03",
//                "#F76114", "#EF5525", "#E74836", "#DF3C47", "#D72F58",
//                "#CF2269", "#C7167A", "#B91686", "#AA1791", "#9C189D",
//                "#8E19A8", "#7F1AB4", "#711BC0", "#621CCB", "#4B0082"], min:1, max:39}, 'edge age')








// build recipe
var recipe_edges = ee.Image([]);

// for each year 
years.forEach(function (year_i) {
    // set temp file
    var tempFile = ee.Image(0);
    // for each edge size 
    edge_sizes.forEach(function (size_i) {
        // read file 
        var edge = ee.Image(edge_asset)
            .select('edge_' + year_i);
        // perform remap 
        edge = ee.Image(0).where(edge.lte(size_i), size_i).selfMask()
        // store edge size 
        tempFile = tempFile.blend(edge).selfMask();
    });
    // store per year 
    recipe_edges = recipe_edges.addBands(tempFile.rename('edge_' + year_i));
});

//Map.addLayer(recipe_edges.select('edge_2023').randomVisualizer(), {}, 'edges')

////////////// patch ************
var patch_asset = 'projects/mapbiomas-brazil/assets/DEGRADATION/COLLECTION-10/public/degradation_patch_size_col101_v2';
var patch_version = '4';
var patch_sizes = [75, 50, 25, 10, 5, 3];

//Map.addLayer(
//    ee.Image(patch_asset).select('size_2023')
//      .updateMask(ee.Image(patch_asset)
//      .select('size_2023')
//      .lte(500)), 
//  {palette: ['#E50C08', '#FFAA5F', '#32CD32','#19B06F', '#6FA8DC','#0B5394',  "#C7167A"], min:1, max:250},
//  'Size')



// build recipe
var recipe_patches = ee.Image([]);

// for each year 
years.forEach(function (year_i) {
    // set temp file
    var tempFile = ee.Image(0);
    // for each patch size 
    patch_sizes.forEach(function (size_i) {
        // read file 
        var patch = ee.Image(patch_asset + 'size_' + size_i + 'ha_v' + patch_version)
            .select('size_' + size_i + 'ha_' + year_i);
        // perform remap 
        patch = patch.remap({
            'from': classList,
            'to': ee.List.repeat({ 'value': size_i, 'count': classList.length })
        });
        // store edge size 
        tempFile = tempFile.blend(patch).selfMask();
    });
    // store per year 
    recipe_patches = recipe_patches.addBands(tempFile.rename('patch_' + year_i));
});


////////////// isolation ************
var isolation_asset = 'projects/mapbiomas-workspace/DEGRADACAO/ISOLATION/';
var isolation_version = '8';
var isolation_bigSize = '1000';
var isolation_medSize = '100';
var isolation_distances = ['05', '10', '20'];

// build recipe
var recipe_isolation = ee.Image([]);

// for each year 
years.forEach(function (year_i) {
    // set temp file
    var tempFile = ee.Image(0);
    // for each patch size 
    isolation_distances.forEach(function (distance_i) {
        // read file 
        var isolation = ee.Image(isolation_asset + 'nat_uso_frag' + isolation_medSize + '__dist' + distance_i + 'k__' + isolation_bigSize + '_v' + isolation_version + '_85_22')
            .select('nat_' + year_i);
        // perform remap 
        isolation = isolation.remap({
            'from': classList,
            'to': ee.List.repeat({ 'value': ee.Number.parse(distance_i), 'count': classList.length })
        });
        // store edge size 
        tempFile = tempFile.blend(isolation).selfMask();
    });
    // store per year 
    recipe_isolation = recipe_isolation.addBands(tempFile.rename('isolation_' + year_i));
});


//////////////////////
// fundiario 
var fundiario = ee.Image('projects/mapbiomas-workspace/AUXILIAR/IMAFLORA2025/malhafundiaria_br_Imaflora_abril2025');

// remap to level_1
fundiario = fundiario.remap({
    'from': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 16, 17, 18, 19, 20, 99, 13, 15, 14, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 116, 117, 118, 119, 120, 199, 113, 115, 114],
    'to': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 12, 1, 2, 2, 8, 99, 13, 15, 14, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 12, 1, 2, 2, 8, 99, 113, 15, 14]
});

var fundiario_l1 = fundiario.remap({
    'from': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 113],
    'to': [1, 1, 2, 2, 2, 1, 1, 3, 3, 3, 1, 1, 2, 3, 2]
}).updateMask(biomes.eq(4));

// get native mask
var native_mask = ee.Image('projects/mapbiomas-workspace/DEGRADACAO/COLECAO/BETA/PROCESS/native_mask/nativeMask_col10_v1')

// mask fundiario by n ative
fundiario_l1 = fundiario_l1.updateMask(native_mask.select('classification_2024').eq(1))

// patch id
var id = ee.Image('projects/mapbiomas-brazil/assets/DEGRADATION/COLLECTION-10/public/degradation_patch_id_col101_v2')

Map.addLayer(id.select('id_1986').randomVisualizer(), {}, 'id 1986')
Map.addLayer(id.select('id_2023').randomVisualizer(), {}, 'id 2023')

// m orphology
var morphology = ee.Image('projects/mapbiomas-brazil/assets/DEGRADATION/COLLECTION-10/public/degradation_patch_morphology_col101_v2')

Map.addLayer(morphology.select('morphology_2023'), { palette: ['34662B', '#9BCFB3', '#46A9B1', '#FFCC4A', '#F6B0CB', '#A9DBEB'], min: 1, max: 6 }, 'morpho')




var veg_sec = ee.Image('projects/mapbiomas-brazil/assets/DEGRADATION/COLLECTION-10/public/degradation_secondaryVegetation_col101_v2')
    .divide(100)
    .round()

Map.addLayer(veg_sec.select('age_2023'), { palette: ['#f3f6c2', '#f1f69a', '#eff672', '#eef64a', '#ecf622', '#d7f622', '#c2f622', '#adf622', '#93f622', '#79f622', '#6ff622', '#62f625', '#58f627', '#4ef629', '#40f62b', '#36f62d', '#2cf62f', '#22f631', '#22e72d', '#22dd2a', '#22c925', '#23b520', '#23ab1d', '#23a11b', '#239718', '#238814', '#237e12', '#247510', '#246b0d', '#24660c', '#24630b', '#255808', '#255808', '#255808', '#255808', '#255808', '#255808', '#255808'], min: 0, max: 39 }, 'veg_sec')

// fire freq
// get lulc
var fire_lulc = ee.Image('projects/mapbiomas-brazil/assets/DEGRADATION/COLLECTION-10/public/degradation-fireFrequency-col101_v2')
    .select('fire_frequency_2023')
    .mod(100).floor()
    .selfMask()

//Map.addLayer(fire_freq.randomVisualizer())

var fire_freq = ee.Image('projects/mapbiomas-brazil/assets/DEGRADATION/COLLECTION-10/public/degradation-fireFrequency-col101_v2')
    .select('fire_frequency_2023')
    .divide(100).round()
    .updateMask(fire_lulc.eq(3).or(fire_lulc.eq(6)))
    .selfMask()


//Map.addLayer(fire_freq, {palette: ["#b00a0a", "#b12e28", "#c15648", "#d58870", "#ecc39f"], min:1, max:5}, 'fire_freq')


// fire age
var fire_age = ee.Image('projects/mapbiomas-brazil/assets/DEGRADATION/COLLECTION-10/public/degradation-fireAge-col101_v2')
    .select('age_2023')
    .divide(100).round()
    .updateMask(fire_lulc.eq(3).or(fire_lulc.eq(6)))
    .selfMask()

//Map.addLayer(fire_age, {palette: ['#800000','#800000','#850708','#8B0E0F','#901417','#961B1E','#9B2226',
//          '#9F2222','#A3211E','#A6211A','#AA2016','#AE2012','#B42E0F','#B93C0C',
//          '#BF4B08','#C45905','#CA6702','#BF7C27','#B4924D','#AAA772','#9FBD98',
//          '#94D2BD','#78C5B5','#5DB9AD','#41ACA6','#26A09E','#0a9294','#008998','#007d96',
//          '#007292','#00688c','#005e86','#00557f','#004c7b','#004080','#003781','#002d81',
//          '#00227f','#00147d','#000079'], min:0, max:39}, 'fire_age')


var mapa = ee.Image()
    .blend(fundo)
    .blend(ee.Image(edge_asset).select('edge_2023').updateMask(ee.Image(edge_asset).select('edge_2023').lte(150)).visualize({ palette: ['red', '#00BFC4', '#00BFC4', '#00BFC4', '#00BFC4', '#00BFC4'], min: 30, max: 150 })
    )


    //.blend(sumLast.visualize(vis))
    //.blend(degrad_freq.visualize({palette: ['#C4C411', '#E17B00', '#A10C0C', '#580651', '#050004', '#32a65e'], min:1, max:6}))
    //.blend(stable.visualize({palette:['#DFDFDF', '#32a65e', '#FFFFB2', ], min:1, max:3}))
    //.blend(ee.Image(edge_asset).select('edge_2023').updateMask(ee.Image(edge_asset).select('edge_2023').lte(150)).visualize({palette:['#FF0001','#32CD32','#19B06F','#6FA8DC','#0B5394','#A64D79','#F54CA9'], min:30, max: 150}))
    //.blend(ee.Image(patch_asset).select('size_2023').updateMask(ee.Image(patch_asset).select('size_2023').lte(500)).visualize({palette: ['#E50C08', '#FFAA5F', '#32CD32','#19B06F', '#6FA8DC','#0B5394',  "#C7167A", "#621CCB"], min:1, max:250}))
    //.blend(ee.Image(edge_age).select('age_2023').visualize({palette:["#228B22", "#2F9420", "#3C9D1F", "#49A61D", "#56AF1C",
    //                "#63B81A", "#70C119", "#7DCA17", "#8AD316", "#97DC14",
    //                "#A4E513", "#B1EE11", "#BEF710", "#CCFF0E", "#D8F20D",
    //                "#E4E50C", "#F0D80B", "#FCCC0A", "#FFBE09", "#FFB108",
    //                "#FFA307", "#FF9606", "#FF8905", "#FF7B04", "#FF6E03",
    //                "#F76114", "#EF5525", "#E74836", "#DF3C47", "#D72F58",
    //                "#CF2269", "#C7167A", "#B91686", "#AA1791", "#9C189D",
    //                "#8E19A8", "#7F1AB4", "#711BC0", "#621CCB", "#4B0082"], min:1, max:39}))
    //.blend(id.select('id_2023').randomVisualizer().visualize())
    //.blend(morphology.select('morphology_2023').visualize({palette:['34662B', '#9BCFB3', '#46A9B1', '#FFCC4A', '#F6B0CB', '#A9DBEB'], min:1, max:6}))
    //.blend(recipe_isolation.select('isolation_2022').visualize({palette: ['#FFAA5F', '#FF0001','#F54CA9'], min:5, max:20}))
    //.blend(veg_sec.select('age_2023').visualize({palette: ['#f3f6c2','#f1f69a','#eff672','#eef64a','#ecf622','#d7f622','#c2f622','#adf622','#93f622','#79f622','#6ff622','#62f625','#58f627','#4ef629','#40f62b','#36f62d','#2cf62f','#22f631','#22e72d','#22dd2a','#22c925','#23b520','#23ab1d','#23a11b','#239718','#238814','#237e12','#247510','#246b0d','#24660c','#24630b','#255808','#255808' ,'#255808' ,'#255808' ,'#255808', '#255808' ,'#255808'], min:0, max:39}))
    //.blend(fire_freq.visualize({palette: ["#b00a0a", "#b12e28", "#c15648", "#d58870", "#ecc39f"], min:1, max:5}))
    //.blend(fire_age.visualize({palette: ['#800000','#800000','#850708','#8B0E0F','#901417','#961B1E','#9B2226',
    //        '#9F2222','#A3211E','#A6211A','#AA2016','#AE2012','#B42E0F','#B93C0C',
    //        '#BF4B08','#C45905','#CA6702','#BF7C27','#B4924D','#AAA772','#9FBD98',
    //        '#94D2BD','#78C5B5','#5DB9AD','#41ACA6','#26A09E','#0a9294','#008998','#007d96',
    //        '#007292','#00688c','#005e86','#00557f','#004c7b','#004080','#003781','#002d81',
    //        '#00227f','#00147d','#000079'], min:0, max:39}))
    // mosaic
    //.blend(mosaic.visualize({
    //    'bands': ['swir1_median', 'nir_median', 'red_median'],
    //    'gain': [0.08, 0.07, 0.2],
    //    'gamma': 0.85
    //}))
    .blend(scale)
    //.blend(vec_estados2)
    //.blend(cerrado_line);
    .blend(biomes_line)
//.blend(fire_regime_change.visualize({palette: [
//      '0000ff',
//      'ffffff', 
//      'ff0000'
//    ], min: -0.5, max: 0.5}))
//.blend(brazil_line)
//.blend(structure.visualize({palette:['#FFFF00', '#FF00E0'], min:4, max:5}))
//.blend(biomas_line)

Map.addLayer(mapa);
var thumb = ui.Thumbnail({
    image: mapa,
    params: {
        dimensions: 2400,
        region: geometry,
        //format: 'PNG'
    },
    //onClick, 
    //style

});
print(thumb);

