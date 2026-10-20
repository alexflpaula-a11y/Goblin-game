# Transformação low-poly — inventário e progresso

O jogo está migrando de pixel art para o estilo **low-poly facetado**
(superfícies de triângulos planos com sombreamento flat, como a arte-fonte
dos animais). Este documento é a fonte da verdade do que já foi feito, do
que falta e de como cada etapa é produzida.

> **Correção de rumo (registrada a pedido):** os animais **já são todos
> low-poly** — lobo comum, Gêmeos da Guerra, javali, veado e lebre nascem
> facetados na arte-fonte (`art-source/wolves-*`, `art-source/war-twins`,
> `art-source/animals-original`, `art-source/gemeos-lowpoly`). Em tamanhos
> pequenos (lobo 48×32) as facetas suavizam na redução, mas o estilo está
> correto e **não** entra na lista de faltantes.

## ✅ Feito — animais (192 sprites)

| Conjunto | Sprites | Origem |
|---|---|---|
| Gêmeos da Guerra (`twin_jaw_*`, `twin_paw_*`) | 79 | IA low-poly 1200×880 → `tools/cut_gemeos_set.py` (ver `art-source/gemeos-lowpoly/README.md`) |
| Lobo comum (`wolf_*`) | 56 | arte low-poly preservada, expandida por `tools/expand_wolf_frames.py` |
| Javali / veado / lebre (`animal_*`) | 57 (19 cada) | arte low-poly; caminhada por `tools/make_walk_legs.py` a partir do repouso |

## ✅ Feito nesta etapa — cenários e estruturas (40 sprites + terreno)

Gerado por **`tools/lowpoly_sprites.py`** (triangulação facetada reprodutível,
sem IA). Os PNGs pixel-art originais ficam preservados em
`art-source/pixelart-cenarios-estruturas/` e a ferramenta sempre lê dali —
re-rodar com outros parâmetros não acumula efeito.

| Grupo | Sprites | Detalhe |
|---|---|---|
| Estruturas da vila | 15 | as 14 construções do catálogo + lona de obra (`building_construction_site`), 64→192 px internos |
| Divindades | 2 + 1 | Grande Árvore, Golem de Pedra e a pedra arremessada (`fx_pedra_divina`) |
| Nós coletáveis | 4 | árvore, toco, rocha, entulho |
| Balão | 3 | destruído / pronto / voando |
| Tocas e baús | 7 | `prop_den`, `prop_den_lair`, `prop_hive`, baús de mapa e de recompensa |
| Fundos | 8 | `bg_den`, `bg_den_twins`, `bg_den_passage`, mar do mapa e os 4 retratos de ilha (640×360→1280×720 nos fundos grandes) |
| **Terreno** (código) | — | `world.js` (ilha da vila) e `raid.js` (ilhas de raid, 4 temas): cada azulejo vira 2 facetas triangulares com tom flat próprio (`facetTile`) |

### Decisões desta etapa

- **Silhueta e âncoras intactas:** o alfa de saída é o alfa original ampliado.
  Base dos prédios, linha dos pés, perspectiva do túnel (`passage.js`) e
  hitboxes não mudam — só a resolução interna cresce (2×–3×), porque todos os
  `drawImage` de cenário têm tamanho de destino fixo.
- **Passe de detalhe:** portas, cordas, serras e lamparinas são linhas finas
  que a média das facetas apaga. Onde a luminância foge da média local, a
  ferramenta reimprime a cor original por cima das facetas. Nos fundos
  grandes esse passe é quase desligado (`detail=0.12`) para não trazer de
  volta o cascalho pixelado da caverna.
- **Suavização só no cenário:** os desenhos de estruturas/nós/balão/tocas/
  baús/fundos ligam `imageSmoothingEnabled` só naquele `drawImage` (a arte
  interna é maior que o desenho) e desligam em seguida. Personagens pixel
  art continuam nítidos sem suavização, como antes.
- **Reproduzível:** seed fixa por sprite (hash do nome). Para ajustar o
  tamanho da faceta de um grupo, edite `TARGETS` em `tools/lowpoly_sprites.py`
  e rode de novo.

```bash
/tmp/pv/bin/python tools/lowpoly_sprites.py            # todos os alvos
/tmp/pv/bin/python tools/lowpoly_sprites.py building_house_1   # um alvo
/tmp/pv/bin/python tools/build_singlefile.py           # rebuild jogável
bash tools/test.sh
```

### Limitações conhecidas desta etapa

- Prédios de madeira marrom-sobre-marrom (Serraria, Quartel, Armazém) ficam
  mais "lama facetada" que os demais; continuam identificáveis pelos
  detalhes reimpressos (serra, bandeira, porta dupla), mas um ajuste fino
  por prédio (aumentar contraste entre telhado/parede na arte-fonte) é o
  caminho se quiser mais leitura.
- As facetas dos prédios são menores que as dos animais em tamanho final
  (prédio é desenhado em 64 px), porque faceta grande apagava portas e
  janelas. Árvores, rochas, Golem e fundos ficaram com facetas maiores.

## ⏳ O que falta (próximas etapas, em ordem sugerida)

| # | Grupo | Sprites | Por que é uma etapa própria |
|---|---|---|---|
| 1 | **Goblins** (`goblin_*`, `variant_*`, `ferro_*` em `assets/sprites/goblins/`) | **2914** | É o personagem principal e o maior bloco: 45 variações × 62 quadros de 32×32 com âncora exata e sistema de composite por camadas. Facetar quadro a quadro com grade fixa por conjunto (a mesma triangulação em todos os frames, senão a faceta "ferve" na animação) é o caminho provável; exige adaptar `gen_goblin_variations.py`/overlays juntos. |
| 2 | **Overlays de equipamento** (`goblin-gear-overlays/`) | 868 | Só fazem sentido junto com os goblins (mesma grade/âncora, gerados de `art-source/equipment-masks/`). |
| 3 | **Conjunto Avaritia** (`av_*`) | 437 | Skins completas; idem, junto dos goblins. Origem em `sprites/itens/gerar_*.py` (recolor) — precisa decidir se o facetado entra antes ou depois do recolor. |
| 4 | **Itens, drops, recursos e habilidades** (`item_*`, `drop_*`, `res_*`, `skill_*`) | 43 | Ícones de 16–32 px desenhados pequenos; facetado pode virar ruído. Provável gerar em 96 px internos com faceta grossa e conferir um a um. |
| 5 | **Ícones e molduras de UI** (`ui_icon_*`, `ui_attack_sword`) | 7 | Rápido (mesma ferramenta), mas convém casar com o item 6. |
| 6 | **UI desenhada por código** (`js/ui.js` e painéis em `main.js`) | — | Placas de madeira, botões e painéis são retângulos/texto hoje; low-poly aqui significa trocar preenchimentos por painéis facetados (triângulos) — mudança de código, não de sprite. |
| 7 | **Props de raid por código** (`drawVent`, `drawStump`, `drawScrap`, `drawOreSpike` em `raid.js`) e partículas quadradas (poeira de obra, fumaça da cozinha, brilho da água, estrelas do baú) | — | Passar os retângulos para polígonos/triângulos; detalhe final de coerência. |

Totais do `assets/manifest.json` (4501 sprites): **feitos 232**
(192 animais + 40 cenário/estruturas) + terreno procedural;
**faltam 4269**, quase todos do bloco goblin/equipamento (4219).

## Como conferir

- Folha antes/depois das estruturas e fundos: `docs/lowpoly-antes-depois.png`.
- No jogo: vila (terreno facetado + prédios), `?mode=test` para construir
  tudo; batalhas em `?demo=battle` / `?demo=twins`; mapa das ilhas pelo balão.
