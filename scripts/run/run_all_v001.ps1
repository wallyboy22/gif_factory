$dataset     = "brasil_degradation_col10_1"
$products    = @(
  "edge_area","edge_age",
  "patch_size","patch_size_fragments","patch_size_massifs",
  "patch_id","landscape_morphology",
  "secondary_vegetation_age","secondary_vegetation_coverage",
  "fire_frequency","natural_coverage",
  "fire_age","burned_natural_coverage",
  "canopy_disturbance_frequency","logging"
)
$territories = @(
  "matopiba_cerrado","biomas",
  "amazonia","caatinga","cerrado","mata_atlantica",
  "pampa","pantanal","bap","bap_planalto"
)

# Gera JSON na ordem do usuario: territorio -> produtos
$items = @()
foreach ($terr in $territories) {
  foreach ($prod in $products) {
    $items += @{dataset=$dataset; product=$prod; territory=$terr}
  }
}
$json = @{items=$items} | ConvertTo-Json -Depth 3
[System.IO.File]::WriteAllText("$PWD\batch_v001.json", $json, [System.Text.UTF8Encoding]::new($false))

Write-Output "Total: $($items.Count) combinacoes | Workers: 6 | Dim: 1560px"
Write-Output "Ordem: territorio -> 15 produtos (sequencia solicitada)"
Write-Output "Dataset: $dataset"
Write-Output "Inicio: $(Get-Date -Format 'HH:mm:ss')"
Write-Output ("="*50)

$env:PYTHONIOENCODING='utf-8'
python -m src.ipam_gif_factory.interfaces.cli --generate --batch batch_v001.json --workers 6 --resume
