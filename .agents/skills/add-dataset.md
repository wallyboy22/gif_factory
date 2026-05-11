# Skill: Adicionar Novo Dataset

## Objective
Add a new Earth Engine dataset to the IPAM GIF Factory system so it becomes available in CLI, Dashboard, and API.

## Steps

### 1. Identify Dataset Info
- **Asset ID:** Full Earth Engine asset path (e.g., `projects/mapbiomas-public/assets/...`)
- **Product Name:** Human-readable name
- **Category:** Existing or new category
- **Bands:** List of band names
- **Temporal Range:** [start_year, end_year] if applicable
- **Visualization Key:** Key from `config/visualization.yaml`

### 2. Edit `config/datasets.yaml`
Add entry under the appropriate category or create a new one:

```yaml
my_new_dataset:
  description: "Description"
  category: "my_category"  
  source: "Source Name"
  products:
    my_product:
      name: "Product Name"
      asset: "projects/.../asset_id"
      bands: ["band1", "band2"]
      temporal_range: [2000, 2024]
```

### 3. Edit `config/visualization.yaml` (if needed)
Add visualization parameters if the product needs a new palette:

```yaml
my_viz:
  name: "My Visualization"
  min: 0  
  max: 100
  palette: ["#ffffff", "#000000"]
  label: "Description"
  cmap_type: "sequential"
```

### 4. Validate YAML
```bash
python -c "import yaml; yaml.safe_load(open('config/datasets.yaml'))"
python -c "import yaml; yaml.safe_load(open('config/visualization.yaml'))"
```

### 5. Test
```bash
python main.py --list-products
python main.py --dataset my_new_dataset --product my_product --territory df --output ./output/test/
```

### 6. Verify
- Check output GIF in `./output/test/`
- Check logs for errors
- Run tests: `pytest tests/`

## Notes
- For composite products (degradation), use `post_processing` field
- For ImageCollections, set `asset_type: image_collection`
- For products needing mosaic, set `mosaic: true`
- Always test with DF territory first (fastest)
