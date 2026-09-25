# 🧌 Vila de Goblins

Jogo mobile-first de **gerenciamento de vila + batalhas por turnos**, em HTML5 Canvas + JavaScript puro (sem dependências). Você controla uma vila de goblins: corte madeira, minere, construa estruturas, fabrique equipamentos, cozinhe, recrute goblins (escolhendo 1 entre 3) e invada outras vilas.

## ▶️ Como jogar

**Sem instalar nada:** abra `release/vila-de-goblins-jogavel.html` no navegador (PC ou celular). É um build de arquivo único com todos os sprites/textos embutidos — funciona offline.

**Modo desenvolvimento:** sirva a pasta e abra `http://localhost:8080`:

```bash
python3 -m http.server 8080
```

### Controles
| Gesto | Ação |
|---|---|
| 1 dedo arrastando | mover a câmera pela ilha |
| Pinça (2 dedos) / roda do mouse | zoom (0.7x–3x) |
| Toque em prédio / nó de recurso | abre menu / envia goblin para trabalhar |
| Botão **Construir** (canto) | painel da Casa de Construção |
| Botão **Vila** | roster de goblins |

## 🗂️ Estrutura

```
assets/
  data/          balance.json, i18n.pt-br.json, i18n.en.json
  manifest.json  lista de sprites (nomes lógicos → caminhos)
  sprites/       PNGs 32×32 por categoria (goblins, buildings, resources, nodes…)
css/style.css    HUD e layout DOM
js/
  main.js        boot, game loop, roteamento de telas
  config.js      resolução lógica 640×360 (paisagem) e constantes
  input.js       gestos multi-toque (pan/pinch/tap) + mouse
  camera.js      câmera livre com clamp na ilha
  world.js       ilha procedural + walkers goblins + floats
  nodes.js       nós de recurso FINITOS (árvore/pedra → toco/entulho)
  village.js     recursos, estruturas, habitação, custos
  goblin.js      entidade: 6 atributos, especialidade, raridade, XP
  ui.js          UI imediata no canvas + visual rústico goblin
  assetLoader.js sprites reais ou placeholder automático (jogo nunca quebra)
  i18n.js        PT-BR / EN em tempo real
  save.js        localStorage + autosave
  balance.js     números do jogo (balance.json)
docs/PLANEJAMENTO.md   planejamento completo + prompts por etapa + log
tools/             shot.py (screenshots), build_singlefile.py, md2docx.py
release/           build jogável de arquivo único
```

## 🎨 Sprites

Todos os sprites são **PNG 32×32 separados**, referenciados por **nome lógico** no `manifest.json`. Se um PNG não existir, um placeholder automático é desenhado (o jogo nunca quebra). Sprites base dos goblins (idle/walk/attack/hurt/death) foram extraídos de um GIF fornecido pelo autor; variantes (espada, armadura, pistola, tapa-olho) virão depois.

## 🔧 Ferramentas

```bash
bash tools/setup_preview.sh                 # instala Playwright p/ screenshots
python3 tools/shot.py <nome> [?demo=...]    # gera prévia em previas/
python3 tools/build_singlefile.py           # gera release/vila-de-goblins-jogavel.html
python3 tools/md2docx.py                    # gera o .docx do planejamento
```

## 🌐 Idiomas

PT-BR e EN com troca em tempo real (botão no HUD). Textos em `assets/data/i18n.*.json`.

## 📜 Status

Fases concluídas: fundação (ilha + câmera), goblins + habitação + recrutamento 1-de-3, recursos finitos + trabalho, UI de construção rústica, orientação paisagem. Roadmap completo em `docs/PLANEJAMENTO.md`.
