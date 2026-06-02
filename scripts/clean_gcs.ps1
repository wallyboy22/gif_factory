Write-Output "Bucket: gs://mapbiomas-fire/gif-factory/"
Write-Output ""
Write-Output "Listando conteudo atual..."
gsutil ls gs://mapbiomas-fire/gif-factory/

Write-Output ""
Write-Output "Deletando tudo em gs://mapbiomas-fire/gif-factory/..."
gsutil -m rm -r gs://mapbiomas-fire/gif-factory/*

Write-Output ""
Write-Output "Verificando..."
gsutil ls gs://mapbiomas-fire/gif-factory/
