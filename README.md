# 🧌 Vila de Goblins

Jogo mobile-first de **gerenciamento de vila + batalhas por turnos**, em HTML5 Canvas + JavaScript puro (sem dependências). Você controla uma vila de goblins: corte madeira, minere, construa estruturas, cumpra missões, cozinhe, recrute goblins (escolhendo 1 entre 3) e — nas próximas fases — invada outras vilas.

## ▶️ Como jogar

**Sem instalar nada:** abra `vila-de-goblins-jogavel.html` no navegador (PC ou celular). É um build de arquivo único com sprites e textos embutidos — funciona offline.

**Modo desenvolvimento:** sirva a pasta e abra `http://localhost:8080`:

```bash
python3 -m http.server 8080
```

### Controles
| Gesto | Ação |
|---|---|
| 1 dedo arrastando | mover a câmera pela ilha |
| Pinça (2 dedos) / roda do mouse | zoom (0.7x–3x) |
| Toque em árvore/pedra/posto | manda o goblin livre mais próximo trabalhar |
| Toque no goblin trabalhando | chama ele de volta |
| Toque num prédio | abre a tela dele |
| Botões no rodapé | **Construir**, **Missões**, **Cozinha**, **Mercado**, **Vila** |

## 🔄 O ciclo do jogo

```
coletar recursos → construir → cumprir missões → XP da vila
   → subir de nível → desbloquear estruturas → fazenda/cozinha
   → curar goblins → vender o excedente no mercado → repetir
```

A **vila sobe de nível** com o XP das missões. Cada nível libera novas estruturas *e* eleva o teto de melhoria de todas elas. Melhorar a Cozinha, por exemplo, desbloqueia pratos melhores.

| Nível | Desbloqueia |
|---|---|
| 1 | Casa de Construção · Casa de Goblin · Painel de Missões |
| 2 | Serraria · Fazenda |
| 3 | Cozinha · Mercado |
| 4 | Mina · Estábulo |
| 5 | Ferraria |
| 6 | Altar · Bazar |
| 7 | Porto |
| 8 | Quartel |

## 🗂️ Estrutura

```
index.html          versão de desenvolvimento (carrega js/ por HTTP)
vila-de-goblins-jogavel.html   build de arquivo único (é o que se distribui)

css/style.css       HUD e layout DOM
js/
  loader.js         mini sistema de módulos (dev e build usam a mesma API)
  main.js           boot, game loop, roteamento de telas
  config.js         resolução lógica 640×360 (paisagem) e constantes
  input.js          gestos multi-toque (pan/pinch/tap) + mouse
  camera.js         câmera livre com clamp na ilha
  world.js          ilha procedural + goblins que passeiam/trabalham
  nodes.js          postos de trabalho: nós finitos + fazenda/mina infinitas
  village.js        recursos, catálogo de estruturas, XP/nível da vila
  goblin.js         entidade: 6 atributos, especialidade, raridade, XP
  quests.js         painel de missões (itens → ouro + XP da vila)
  cooking.js        receitas, pratos que curam
  market.js         mercado: vender e comprar por ouro
  gear.js           conjunto Avaritia: armaduras da loja (compra única)
  ui.js             UI imediata no canvas + visual rústico goblin
  assetLoader.js    sprites reais ou placeholder automático
  i18n.js           PT-BR / EN em tempo real
  save.js           localStorage + autosave
  balance.js        carrega o balance.json
assets/
  data/             balance.json, i18n.pt-br.json, i18n.en.json
  manifest.json     lista de sprites (nomes lógicos → caminhos)
  sprites/          PNGs 32×32 por categoria
tools/              build, testes e geração de sprites
planejamento-jogo-gnomos.md   planejamento completo + log de desenvolvimento
```

## 🔧 Ferramentas

```bash
python3 tools/build_singlefile.py   # gera o vila-de-goblins-jogavel.html
python3 tools/gen_sprites.py        # (re)gera a pixel art de prédios e comidas
python3 tools/unbuild.py            # extrai a fonte de volta a partir do build
bash    tools/test.sh               # roda as 4 suítes de teste
```

> **Importante:** depois de mexer em `js/`, `css/` ou `assets/`, rode o
> `build_singlefile.py` — senão o arquivo jogável fica para trás.

## ✅ Testes

192 testes automatizados, sem navegador (`bash tools/test.sh`):

| Suíte | O que cobre |
|---|---|
| `smoke` | lógica pura: vila, goblins, missões, cozinha, save |
| `render` | as 6 telas desenham sem erro; traduções e sprites conferidos |
| `playthrough` | uma partida inteira — o ciclo do jogo fecha do início ao fim |
| `build` | o arquivo único distribuído sobe sozinho |

## 🎨 Sprites

O conjunto **Avaritia** (peitoral, calça, capacete + 3 pares + conjunto completo, 62 frames cada) vive em `sprites/itens/` e é gerado por `sprites/itens/gerar_item.py` / `gerar_conjunto.py` a partir dos frames do goblin no `window.EMBEDDED` do jogo — apenas recolor de pixels existentes.

PNGs **32×32** referenciados por **nome lógico** no `manifest.json`. Se um PNG não existir, um placeholder é desenhado automaticamente (o jogo nunca quebra). Os goblins vieram de um GIF do autor (idle/walk/attack/hurt/death); prédios, recursos e comidas são pixel art autoral gerada por `tools/gen_sprites.py`.

## 🌐 Idiomas

PT-BR e EN com troca em tempo real (botão no HUD). Textos em `assets/data/i18n.*.json`.

## 📜 Status

**Fase 1 concluída (1.1 → 1.8):** ilha + câmera, goblins + habitação + recrutamento 1-de-3, recursos finitos, trabalho, construção de todas as estruturas, missões, XP/nível da vila, cozinha, fontes renováveis e **Mercado** (vender o excedente por ouro, comprar o que falta) — incluindo a **loja de armaduras Avaritia**: Peitoral (120 ouro), Calça (90) e Capacete (150), compra única; cada peça adquirida veste a vila inteira (individual → pares → conjunto completo, sprites gerados por recolor em `sprites/itens/`, sem pixels novos).

**A seguir:** Fase 2 (Ferraria, equipar, Altar, Bazar) → Fase 3 (combate por turnos). Roadmap completo em `planejamento-jogo-gnomos.md`.
