# Skill: Identidade Visual IPAM no Dashboard

## Objetivo
Aplicar a identidade visual do IPAM no dashboard Streamlit usando CSS customizado,
conforme o Manual de Identidade Visual (2016).

## Sistema de Cores (do Manual IPAM)

| Função | HEX | RGB | Uso |
|--------|-----|-----|-----|
| Verde IPAM (primary) | `#006b3f` | 0,107,63 | Header gradient, tabs ativas, bordas de card, botões primários |
| Verde escuro | `#0d8642` | 14,135,67 | Header gradient (final) |
| Verde claro (secondary) | `#21a54a` | 34,166,74 | Borda lateral de expanders |
| Cinza escuro | `#353935` | 54,57,53 | Texto principal, títulos |
| Cinza médio (web) | `#5a5855` | 91,88,86 | Texto secundário, captions, footer |
| Bege | `#f4ede5` | 244,237,229 | Fundo de tabs inativas, hover expanders |
| Bege claro | `#f9f9f7` | 249,249,247 | Fundo de expanders, containers de métricas |
| Azul IPAM | `#2c479d` | 44,71,158 | Links (uso futuro) |

## Tipografia

- **Web**: Roboto (Google Fonts) — Bold headings, Regular body, Light captions
- **Import**: `@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');`

## Componentes Estilizados

### Header
```css
.ipam-header {
    background: linear-gradient(135deg, #006b3f, #0d8642);
    padding: 1.2rem 2rem;
    border-radius: 0 0 14px 14px;
    margin: -1rem -2rem 1.8rem -2rem;
    display: flex; align-items: center; gap: 1.2rem;
}
```
- Contém logo IPAM (branca, transparente) + título "GIF Factory" + subtítulo "Módulo de Degradação · MapBiomas"

### Tabs (Pill Style)
- Background bege `#f4ede5`, border-radius 30px
- Tab ativa: fundo verde IPAM, texto branco
- Tab inativa: fundo transparente, texto cinza escuro
- `tab-highlight` oculto

### Expanders (Gavetas)
- Borda lateral esquerda verde claro (4px)
- Background bege claro
- Border-radius 8px, sombra suave
- Hover: background bege

### Botões
- **Primary** (`type="primary"`): bg verde IPAM, texto branco, border-radius 8px
- **Download**: compacto, padding 0px 8px, font-size 12px
- **Outline**: default Streamlit com border-radius 8px

### Cards de Métrica (Monitoramento)
- Background bege claro, border-radius 12px
- Borda lateral verde IPAM (4px)
- Label: Roboto, cor cinza médio
- Value: Roboto Bold, cor verde IPAM

## Logo
- Arquivo: `references/logo_ipam_30_anos_fundo_transparente_log_branca.png`
- Lido como base64 e embutido no HTML (evita problemas de caminho relativo)

## Como Modificar
1. Edite a variável `_IPAM_CSS` em `dashboard.py`
2. Altere as cores nos seletores CSS
3. Para adicionar novos componentes, crie classes CSS e use `st.markdown(..., unsafe_allow_html=True)`

## Teste
1. Execute: `streamlit run src/ipam_gif_factory/interfaces/dashboard.py`
2. Verifique header verde com logo IPAM
3. Verifique tabs estilo pill
4. Verifique expanders com borda verde
5. Verifique botões compactos e cards de métrica
