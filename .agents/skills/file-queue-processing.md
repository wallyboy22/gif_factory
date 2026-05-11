# Skill: Fila de Processamento com Arquivos

## Objetivo
Gerenciar a fila de processamento de produtos usando arquivos JSON em vez de `st.session_state`,
eliminando o reset do Streamlit ao recarregar a página.

## Arquivos Gerenciados

| Arquivo | Função | Formato |
|---------|--------|---------|
| `queue.json` | Fila de itens pendentes + item atual | `{"items": [[ds, prod, terr], ...], "current": null}` |
| `status.json` | Status do processamento em tempo real | `{"current": [...], "done": bool, "message": str, "start_time": float, "estimate": float, "progress": float}` |

## Fluxo

```
Usuário clica "Processar" / "Processar Todos"
  │
  ├─ _queue_load() → lê queue.json
  ├─ Adiciona item(s) à lista
  ├─ _queue_save() → escreve queue.json
  └─ st.rerun()
        │
        ├─ _render_dev() executa novamente
        ├─ Checa: status.done == True AND queue.items existe?
        │     └─ SIM → inicia thread com _proc_worker()
        │           ├─ Define current em queue.json
        │           ├─ Define status como done=False
        │           ├─ Thread:
        │           │     ├─ Executa CLI: python -m src...cli --generate ...
        │           │     ├─ Lê stdout linha a linha → _status_save()
        │           │     └─ Quando termina → done=True em status.json
        │           └─ st.rerun()
        │
        └─ Mostra progresso lendo de status.json
              ├─ elapsed, progress bar, mensagens
              └─ <meta refresh 3s> para atualizar
```

## Funções do Sistema

### `_queue_load()` / `_queue_save()`
- Lê/escreve `queue.json` na raiz do projeto
- Retorna `{"items": [], "current": None}` se arquivo não existe ou corrompido
- `current` armazena o item sendo processado no momento

### `_status_load()` / `_status_save()`
- Lê/escreve `status.json` na raiz do projeto
- Campos: `current`, `done`, `message`, `start_time`, `estimate`, `progress`
- Retorna estado padrão (tudo vazio) se arquivo não existe

### `_proc_worker(item)`
- Roda em uma `threading.Thread` separada
- Executa `subprocess.Popen` com o comando CLI
- Lê stdout em tempo real e atualiza `status.json`
- No final (`finally`): limpa `current` na queue e marca `done=True` no status

## Vantagens sobre Session State

| Problema | Solução |
|----------|---------|
| Reset no rerun do Streamlit | Dados persistem em arquivo |
| Perda ao recarregar página | Fila continua após F5 |
| Colisão entre usuários | Cada instância tem seus próprios arquivos |
| Depuração | Arquivos JSON legíveis e editáveis manualmente |

## Como Limpar a Fila Manualmente
```bash
echo '{"items":[]}' > queue.json
echo '{"current":null,"done":true,"message":"","start_time":0,"estimate":null,"progress":0}' > status.json
```

## Teste
1. Abra o dashboard: `streamlit run src/ipam_gif_factory/interfaces/dashboard.py`
2. Vá para aba "Dev (Processar)"
3. Selecione filtros, clique "Processar Todos"
4. Verifique se `queue.json` e `status.json` foram criados
5. Recarregue a página (F5) — o processamento continua
