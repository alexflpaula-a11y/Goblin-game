# 🧙‍♂️ PLANEJAMENTO COMPLETO — Jogo de Vila de Goblins
### Gerenciamento + Batalha por Turnos · Mobile (HTML5/Canvas)

> **Documento vivo**: vamos evoluindo ele conforme o jogo cresce. Cada Etapa tem um **prompt pronto para copiar e colar** aqui no chat.

---

## 1. DECISÕES TRAVADAS (ajustáveis)

| Decisão | Escolha |
|---|---|
| Plataforma | **HTML5 + JavaScript (Canvas)** — roda no navegador do celular/PC |
| Foco | **Mobile-first** (toque, orientação retrato, botões na tela) |
| Sprites | **Pixel art 32×32**, entregues como **arquivos PNG separados** |
| Idioma | **Bilíngue PT-BR + EN** (troca em tempo real) |
| Motor | JavaScript puro + Canvas (sem dependências externas) |
| Orientação | **Paisagem (landscape)** — resolução lógica **640×360**, escala automática; `screen.orientation.lock('landscape')` quando suportado |
| Salvamento | `localStorage` (JSON) com auto-save |
| Empacotamento futuro | PWA (instalar no celular) e depois APK via Capacitor |
| Raça jogável | **Goblins** (antes "gnomos") — sprites base fornecidos pelo usuário (GIF com idle/walk/attack/hurt/death), variantes futuras: espada, armadura, pistola, tapa-olho |
| Mundo | **Ilha grande** (1920×1440 px, 120×90 tiles de 16px) com **câmera livre**: 1 dedo = pan, pinça = zoom (0.7–3x), roda do mouse = zoom |
| Prévias | Como o usuário **não abre o preview ao vivo**, cada etapa gera **screenshots PNG reais** em `/home/user/previas/` (Playwright headless) |
| Arte | **Sem placeholders visíveis**: todos os sprites do manifest atual existem como PNG real (goblins extraídos do GIF + pixel art autoral de prédios/recursos/nós) |

---

## 2. VISÃO GERAL DO JOGO

### 2.1 O loop principal (ciclo do jogador)
1. **Começo** — a vila nasce com **Casa de Construção**, **1 Casa de Goblin** (1 goblin) e **Painel de Missões**.
2. **Coletar** — o goblin corta **árvores** e quebra **pedras** espalhadas na vila (nós **finitos** — eles acabam!).
3. **Expandir** — na **Casa de Construção** você cria as outras estruturas (Serraria, Fazenda, Cozinha, Mina, Mercado, Estábulo, Ferraria, Altar, Porto...).
4. **Habitar** — **cada casa cabe 1 goblin**; ao **construir uma casa nova ou melhorar uma existente**, aparecem **3 goblins** e você escolhe **1 deles** (status/classes diferentes). Quanto mais goblins você já recrutou, **maior a chance** de o próximo ter características raras.
5. **Cumprir missões** — o **Painel de Missões** pede itens em troca de **ouro + XP da vila**.
6. **Fabricar** — Ferraria (armas/armaduras), Altar (runas/talismãs/magias/encantamentos), Cozinha (comidas que curam).
7. **Vender** — no Mercado, vender comida/itens; o **Barqueiro** (via Porto) traz itens de fora.
8. **Lutar** — campanha por fases: invadir vilas de goblins inimigas com um **time de até 4 goblins** (você pode ter mais goblins na vila do que os 4 que lutam — escolha a equipe antes da batalha); **chefe no fim de cada fase** (dá **item especial do chefe**); cada fase rende **ouro + XP** e, na **primeira** conclusão, um **baú de prêmios**.
9. **Evoluir a vila** — com o **XP da vila** ela sobe de nível: **desbloqueia estruturas novas** e **libera melhoria de estruturas** (que por sua vez desbloqueiam **equipamentos e comidas melhores**).
10. **Explorar o mapa** — após a 1ª fase, é preciso **consertar e evoluir o Mapa** para liberar as próximas vilas (fases). Fases podem ser **repetidas** por ouro+XP, mas **sem os baús**.

### 2.2 Atributos dos goblins (fixos no design)
| Atributo | Papel |
|---|---|
| 💪 Poder Destrutivo (Força) | Dano físico, carregar mais recursos |
| ✨ Potencial Mágico | Dano/efeito de magias e encantamentos |
| ❤️ Vitalidade | HP máximo e cura recebida |
| 🏃 Velocidade | Ordem de turno e esquiva |
| 🎯 Precisão | Chance de acerto e crítico |
| 📈 Potencial de Evolução | Ganho de XP e bônus ao subir de nível |

### 2.3 Especialidades (todo goblin luta e trabalha, mas com bônus)
**Guerreiro** (+dano físico) · **Mago** (+dano mágico) · **Curandeiro** (cura +) · **Cozinheiro** (comida melhor) · **Trabalhador** (+produção) · **Corredor** (+velocidade) · **Comum** (sem bônus — "não é bom em nada", mas barato e flexível).

### 2.4 Dois sistemas de progressão (importante não confundir)
| Sistema | Como ganha | O que libera |
|---|---|---|
| **XP do goblin** | Batalhas, trabalho | Nível do goblin, atributos, talentos |
| **XP da vila** | Missões e batalhas | Nível da vila: novas estruturas + limite de melhoria das estruturas |

### 2.5 Estruturas (lista completa)
| Estrutura | Função | Desbloqueio |
|---|---|---|
| 🏗️ **Casa de Construção** | Hub: cria e melhora todas as estruturas | Inicial (nível 1) |
| 🏠 **Casa de Goblin** | Habitação (1 goblin por casa; construir/melhorar → escolher 1 de 3) | Inicial (nível 1) |
| 📜 **Painel de Missões** | Missões: itens → ouro + XP da vila | Inicial (nível 1) |
| 🪵 **Serraria** | Eficiência na madeira | Vila nível 2 |
| 🌾 **Fazenda** | Planta comida e (depois) árvores | Vila nível 2 |
| 🍲 **Cozinha** | Cozinha comidas que curam | Vila nível 3 |
| 💰 **Mercado** | Vender e comprar | Vila nível 3 |
| ⛏️ **Mina** | Pedra/minério **infinitos** (recursos naturais acabam) | Vila nível 4 |
| 🐴 **Estábulo** | Montarias/bônus de trabalho | Vila nível 4 |
| ⚒️ **Ferraria** | Armas e armaduras | Vila nível 5 |
| 🔮 **Altar** | Runas, talismãs, magias, encantamentos | Vila nível 6 |
| 🧺 **Bazar** | Trocar goblins: doar 1 (custa ouro) e escolher 1 entre 3 de **nível equivalente** | Vila nível 6 |
| ⚓ **Porto** | Libera o **Barqueiro** (comerciante itinerante) | Vila nível 7 |
| 🏰 **Quartel** | Expedições, bônus de combate | Vila nível 8 |

> **Todas** as estruturas podem ser **melhoradas** (nível 1–3+). A melhoria é limitada pelo **nível da vila** e, ao melhorar, **desbloqueia equipamentos e comidas melhores** (ex.: Ferraria nv.2 → armas de ferro; Cozinha nv.2 → sopas/banquetes).

### 2.6 Recursos finitos e renováveis
- **Naturais (finitos):** Árvores (madeira) e Pedras (pedra) espalhadas na vila — **acabam** depois de coletados.
- **Renováveis:** construir **Mina** (pedra/minério infinitos) e **plantar árvores** (madeira renovável) — liberados conforme a vila evolui.
- **Limite de tamanho da vila:** a grade tem área máxima; expandir custa recursos e exige nível da vila.

---

## 3. ARQUITETURA TÉCNICA

```
/home/user/gnome-village/
├── index.html               → página única + <canvas>
├── css/style.css            → UI sobreposta (HUD, botões, menus)
├── js/
│   ├── main.js              → boot, game loop
│   ├── config.js            → constantes (resolução, balanceamento)
│   ├── input.js             → toque/mouse, botões virtuais
│   ├── assetLoader.js       → carrega PNGs + placeholders
│   ├── i18n.js              → PT-BR / EN
│   ├── save.js              → salvar/carregar (localStorage)
│   ├── state.js             → estado global do jogo
│   ├── village.js           → nível da vila, XP, desbloqueios, limites de melhoria
│   ├── goblin.js             → goblin: atributos, nível, XP, especialidade
│   ├── jobs.js              → trabalho/produção (cortar, minerar, plantar)
│   ├── resources.js         → recursos (finitos/renováveis) e inventário
│   ├── buildings.js         → construções, melhorias, habitação
│   ├── quests.js            → painel de missões
│   ├── crafting.js          → receitas (armas, runas, comidas...)
│   ├── market.js            → mercado (compra/venda)
│   ├── bazaar.js            → bazar (doar/trocar goblins)
│   ├── trader.js            → barqueiro do porto (itens itinerantes)
│   ├── battle.js            → combate por turnos
│   ├── abilities.js         → habilidades, magias, buffs
│   ├── campaign.js          → fases, chefes, baús, recompensas
│   ├── map.js               → mapa: consertar/evoluir, repetir fases
│   └── ui/                  → telas (HUD, vila, batalha, menus)
├── assets/
│   ├── sprites/             → PNGs que VOCÊ vai criar (convenção abaixo)
│   ├── manifest.json        → lista de sprites esperados + fallback
│   ├── audio/               → efeitos sonoros (opcional)
│   └── data/
│       ├── i18n.pt-br.json  → textos PT-BR
│       ├── i18n.en.json     → textos EN
│       └── balance.json     → números de balanceamento (fácil ajustar)
```

**Princípios importantes:**
- **Sprites desacoplados do código**: o código referencia **nomes lógicos** (`goblin_idle`), nunca caminhos de arquivo. Você solta o PNG no lugar do placeholder sem tocar no código.
- **Placeholders automáticos**: enquanto o PNG real não existe, o loader desenha um quadrado colorido com o nome — o jogo **sempre funciona**.
- **Balanceamento em JSON**: dano, preços, custos, XP e níveis ficam em `balance.json`.

---

## 4. CONVENÇÃO DE SPRITES (IMPORTANTE — leia antes de desenhar)

### 4.1 Formato e tamanho
- **32×32 px** por tile/objeto. Personagens: 32×32. Chefe: 32×48 ou 64×64.
- Fundo **transparente**, formato **PNG**.
- Animações = **arquivos numerados** (`walk_0.png`, `walk_1.png`, `walk_2.png`, `walk_3.png`).
- Exporte em **escala 1:1** (32×32 de verdade). Se exportar maior, avise que configuro o `scale`.

### 4.2 Nomeação (obrigatória)
```
assets/sprites/goblins/    goblin_<especialidade>_<acao>_<frame>.png
assets/sprites/buildings/ building_<nome>_<nivel>.png
assets/sprites/items/     item_<nome>.png
assets/sprites/resources/ res_<nome>.png      → ícones
assets/sprites/nodes/     node_<nome>.png     → árvores, pedras (nós de coleta)
assets/sprites/tiles/     tile_<nome>.png
assets/sprites/ui/        ui_<nome>.png
assets/sprites/enemies/   enemy_<nome>_<acao>_<frame>.png
assets/sprites/bosses/    boss_<nome>_<acao>_<frame>.png
assets/sprites/fx/        fx_<nome>_<frame>.png
assets/sprites/misc/      misc_<nome>.png     → baú, mapa, barco, itens de chefe
```
Exemplos reais:
```
goblin_warrior_idle_0.png      goblin_warrior_walk_0.png
building_house_1.png          building_blacksmith_3.png
building_construction_1.png   building_questboard_1.png   building_port_1.png
node_tree_0.png               node_rock_0.png
item_sword_iron.png           res_wood.png   res_gold.png
misc_chest.png                misc_map_1.png   misc_boat.png
boss_king_item.png            (item especial do chefe, ex.: item_boss_axe.png)
```

### 4.3 Equipamento SEM desenhar mil combinações
- **Armas/ferramentas** → PNGs pequenos separados, **desenhados por cima da mão** do goblin em tempo de execução.
- **Armaduras** → sobreposição sutil (peitoral/capacete) ou **tintura de cor** no corpo.
- **Runas/talismãs** → ícones na UI + brilho no goblin.
*(Decidimos o visual fino na Etapa 2.3, mas a arquitetura já está pronta.)*

### 4.4 Ordem de prioridade para você desenhar
| Prioridade | Sprites | Uso |
|---|---|---|
| 🔴 1 | 1 goblin (idle + walk + work, 4 frames cada) | testar movimento e trabalho |
| 🔴 2 | Ícones de recursos (madeira, pedra, minério, ouro, comida) | HUD e inventário |
| 🔴 3 | Tiles + nós de coleta (árvore, pedra) + baú | mapa da vila |
| 🟠 4 | Edifícios iniciais (casa de construção, casa de goblin, painel de missões) | começo do jogo |
| 🟠 5 | Edifícios nível 1 (serraria, fazenda, cozinha, mina, mercado, ferraria, estábulo, altar, bazar, porto) | construção |
| 🟠 6 | 2–3 inimigos + 1 chefe + item especial do chefe | primeira batalha |
| 🟡 7 | Armas/ferramentas (machado, picareta, espada, cajado) | overlay de equipamento |
| 🟡 8 | Ícones de itens (poções, runas, talismãs, comidas) | crafting/inventário |
| 🟢 9 | UI (coração, mana, botões, setas, XP da vila) + mapa + barco | HUD e campanha |
| 🟢 10 | Efeitos (corte, faísca, cura, brilho) | feedback de batalha |

---

## 5. PLANO PASSO A PASSO (POR PRIORIDADE)

> **Como usar**: leia a Etapa, cole o **prompt** no chat quando quiser que eu execute. Cada etapa termina **jogável/visível**. Os "🎨 Sprite hook" indicam onde sua arte entra.

---

## 🟢 FASE 0 — FUNDAÇÃO (2 etapas)

### Etapa 0.1 — Base do projeto + game loop mobile
**O que será feito:** estrutura de pastas, `index.html`, canvas responsivo, game loop (`requestAnimationFrame` + delta time), toque/mouse, HUD de teste, resolução lógica 360×640 com `devicePixelRatio`.

**🎨 Sprite hook:** nada ainda (só quadrados de teste).

**Prompt 0.1:**
```
Crie a base do jogo "Vila de Goblins" em HTML5 Canvas + JavaScript puro,
mobile-first, sem dependências externas. Estrutura: index.html, css/style.css
e js/ com módulos (main, config, input). Canvas em orientação retrato com
resolução lógica 360x640, escalando para caber na tela mantendo proporção
(use devicePixelRatio para nitidez). Implemente um game loop com
requestAnimationFrame e delta time, e detecção de toque/mouse unificada.
Mostre um HUD de teste com FPS e um quadrado que se move com o dedo.
Deixe tudo comentado e modularizado para crescermos em cima.
```

---

### Etapa 0.2 — Asset loader + placeholders + i18n + save
**O que será feito:** `assetLoader.js` (carrega `manifest.json`; PNG ausente → placeholder), `i18n.js` (PT/EN em tempo real), `save.js` (localStorage + autosave).

**🎨 Sprite hook:** nasce a convenção de nomes — você já pode ir desenhando 🔴1 e 🔴2.

**Prompt 0.2:**
```
Implemente no projeto: (1) assetLoader.js que lê assets/manifest.json e carrega
PNGs; para qualquer sprite ausente, desenhe um placeholder automático (quadrado
colorido com o nome lógico) para o jogo nunca quebrar. (2) sistema i18n com
arquivos i18n.pt-br.json e i18n.en.json e troca de idioma em tempo real
(botão PT/EN). (3) save.js com salvar/carregar via localStorage e autosave
a cada 10s. Crie o manifest.json com as categorias: goblins, buildings, items,
resources, nodes, tiles, ui, enemies, bosses, fx, misc. Teste mostrando um
sprite placeholder e o nome de um botão traduzido nos dois idiomas.
```

---

---

### Etapa 0.3 — Ilha grande + câmera livre + sprites base dos goblins ✅ CONCLUÍDA
**O que foi feito:**
- `camera.js`: pan (1 dedo), zoom por pinça no ponto médio, zoom pela roda, clamp nas bordas da ilha, zoom 0.7–3x.
- `world.js`: ilha procedural (noise com semente fixa): mar profundo/raso, areia com beirada molhada, grama com tufos/flores, rochas; clareira central da vila; terreno pré-renderizado em canvas offscreen + brilho animado da água.
- `input.js` reescrito para gestos multi-toque (pan/pinch/tap/wheel).
- **Sprites base dos goblins**: GIF do usuário (40 frames, 5 animações) extraído em PNGs 32×32 transparentes: `goblin_idle_0..4`, `goblin_walk_0..7`, `goblin_attack_0..16`, `goblin_hurt_0..16`, `goblin_death_0..14` (fator pixel 4x reduzido, sombra removida).
- 3 goblins passeando na clareira com idle/walk + sombra + espelhamento.

**🎨 Variantes futuras (definidas pelo usuário, para depois):** espada no lugar da faca, armadura, pistola, tapa-olho e outros detalhes de diferenciação.

---

## 🟡 FASE 1 — NÚCLEO: GERENCIAMENTO DA VILA (8 etapas)

### Etapa 1.1 — Goblins + habitação (1 casa = 1 goblin, escolha entre 3)
**O que será feito:**
- Classe `Goblin`: nome (gerador), especialidade, 6 atributos, nível, XP, HP/MP.
- **Habitação**: cada Casa de Goblin abriga **1 goblin**. Sem casa livre = sem goblin novo.
- **Construir casa nova OU melhorar casa existente** → aparecem **3 goblins candidatos** para escolher **1** (status e classes diferentes).
- **Sorte crescente**: quanto mais goblins você já recrutou, **maior a chance** de o próximo ter características raras (atributos altos, classes especiais, talentos).
- Painel de detalhes ao tocar.

**🎨 Sprite hook:** `goblin_*_idle_0.png` (placeholder até você entregar o goblin real).

**Prompt 1.1:**
```
Crie a entidade Goblin em js/goblin.js com: nome (gerador aleatório), especialidade
(warrior, mage, healer, cook, worker, runner, common) e os 6 atributos:
poderDestrutivo, potencialMagico, vitalidade, velocidade, precisao,
potencialEvolucao (valores 1-10). HP derivado da vitalidade, MP do potencial
mágico. Funções de nível e XP (subir de nível aumenta atributos com bônus extra
pelo potencialEvolucao). Implemente habitação: cada Casa de Goblin abriga 1 goblin;
o jogo começa com 1 casa e 1 goblin. Ao CONSTRUIR uma casa nova ou MELHORAR uma
casa existente, aparecem 3 goblins candidatos (status e classes diferentes) e o
jogador escolhe 1. Implemente sorte crescente: a chance de candidatos raros
(atributos altos, classes especiais, talentos) aumenta conforme o total de goblins
já recrutados (probabilidades e fatores em balance.json). Crie lista + painel de
detalhes ao tocar. Use sprites placeholder com nome lógico por especialidade.
```

---

### Etapa 1.2 — Recursos + nós finitos + HUD
**O que será feito:**
- Recursos: Madeira, Pedra, Minério, Comida (tipos), Ouro.
- **Nós de coleta finitos**: árvores e pedras na vila com quantidade limitada (acabam).
- Inventário + HUD no topo.

**🎨 Sprite hook:** ícones de recursos (🔴2) + nós árvore/pedra (🔴3).

**Prompt 1.2:**
```
Crie js/resources.js com os recursos: madeira, pedra, minerio, comida e ouro.
Implemente nós de coleta finitos: árvores (madeira) e pedras (pedra) com
quantidade limitada que acabam ao serem coletados. Inventário com
add/remove/verificação. HUD no topo mostrando madeira, pedra, minério, comida e
ouro com ícones placeholder. Tudo lido do balance.json.
```

---

### Etapa 1.3 — Trabalho: cortar, minerar, plantar
**O que será feito:**
- Atribuir goblin a trabalho (lenhador → árvore, minerador → pedra, fazendeiro → plantio).
- Ticks de produção; força acelera; especialidade Trabalhador tem bônus.
- **Renováveis (futuro):** Mina (pedra/minério infinitos) e plantio de árvores (madeira renovável).

**🎨 Sprite hook:** animações `walk` e `work` (🔴1).

**Prompt 1.3:**
```
Implemente js/jobs.js: atribuir goblins a trabalhos (lenhador corta árvores,
minerador quebra pedras, fazendeiro planta e colhe comida). Nós de coleta são
finitos e somem ao esgotar. Cada trabalho tem tempo por ciclo; produção acelerada
pela força (poderDestrutivo) e pela especialidade worker. O goblin se desloca até o
posto (movimento A→B). UI de atribuição por toque (goblin → posto). Mostre o
progresso de produção em cada posto. Deixe preparado o sistema para fontes
renováveis (mina e plantio de árvores) que chegam em etapas futuras.
```

---

### Etapa 1.4 — Cozinha: comida que cura
**O que será feito:**
- Receitas (Pão, Sopa, Ensopado, Banquete) usando ingredientes da fazenda.
- Comida tem cura e valor de venda; goblins comem para recuperar HP.
- Bônus da especialidade Cozinheiro. Receitas melhores vêm de melhorar a Cozinha.

**🎨 Sprite hook:** ícones de comidas (`item_bread.png`, `item_soup.png`...).

**Prompt 1.4:**
```
Implemente cozinhar: receitas de comida que consomem ingredientes da fazenda e
produzem pratos com valor de cura (pão, sopa, ensopado, banquete). A cura extra
vem da especialidade cook do goblin que cozinha. Ação "Comer" para curar goblins
fora de batalha. Cada prato tem preço de venda. Estruture as receitas por nível
da Cozinha (melhorar a Cozinha desbloqueia pratos melhores). Mostre os pratos no
inventário.
```

---

### Etapa 1.5 — Casa de Construção: criar e melhorar estruturas
**O que será feito:**
- A **Casa de Construção** é o hub onde se cria/melhora todas as estruturas.
- Grade da vila com **limite de tamanho** (expandir custa recursos + nível da vila).
- Todas as estruturas são melhoráveis (nível 1–3+); melhoria limitada pelo nível da vila.
- Edifícios: Serraria, Fazenda, Cozinha, Mina, Mercado, Estábulo, Ferraria, Altar, Porto, Quartel.

**🎨 Sprite hook:** tiles (🔴3) + edifícios iniciais (🟠4) e nível 1 (🟠5).

**Prompt 1.5:**
```
Implemente js/buildings.js com a Casa de Construção como hub central: abrir a
Casa de Construção mostra o catálogo de estruturas para criar e melhorar.
Grade da vila com limite de tamanho (expansão custa recursos e exige nível da
vila). Estruturas: serraria, fazenda, cozinha, mina, mercado, estabulo, ferraria,
altar, porto, quartel — cada uma com custo, nível 1 a 3+, e efeitos. Bloquear
criação sem recursos ou sem o nível da vila necessário. Melhoria de estrutura
limitada pelo nível da vila. UI de construção por toque (catálogo → escolher →
tocar no tile). Mostre placeholders nomeados.
```

---

### Etapa 1.6 — Mercado: vender e comprar
**O que será feito:** vender comida/recursos/itens por ouro; comprar recursos e itens básicos; preços em `balance.json`.

**🎨 Sprite hook:** ícones de itens (🟡8).

**Prompt 1.6:**
```
Implemente js/market.js: tela de mercado onde o jogador vende (comida, recursos,
itens) e compra (recursos, poções, ingredientes) usando ouro. Preços em
balance.json. Quantidade com botões +/- e confirmação. Atualize o HUD de ouro.
Navegação 100% por toque.
```

---

### Etapa 1.7 — Painel de Missões
**O que será feito:**
- Painel sempre com missões ativas: **entregar itens → ouro + XP da vila**.
- Missões renovam com o tempo (slots fixos, ex.: 3 missões simultâneas).
- Missões geradas com base no nível da vila (dificuldade/recompensa crescente).

**🎨 Sprite hook:** `building_questboard_1.png` (🟠4).

**Prompt 1.7:**
```
Implemente js/quests.js com o Painel de Missões: sempre com missões ativas que
pedem itens (ex.: 5 madeiras, 3 pães) em troca de ouro + XP da vila. Slots fixos
(ex.: 3 missões simultâneas), renovação automática com o tempo, e geração de
missões escalonada pelo nível da vila (recompensas e exigências crescentes).
UI de aceitar/entregar missão e recompensa. Integre o XP da vila (a ser usado na
próxima etapa).
```

---

### Etapa 1.8 — XP e nível da vila (desbloqueios) + ciclo fechado
**O que será feito:**
- `village.js`: XP da vila (de missões e batalhas) → nível da vila.
- A cada nível: **desbloqueia estruturas novas** e **libera melhoria de estruturas** até aquele nível.
- Melhorar estruturas **desbloqueia equipamentos e comidas melhores**.
- Integrar o ciclo: coletar → construir → cozinhar → vender → missões → evoluir.

**Prompt 1.8:**
```
Implemente js/village.js: XP e nível da vila. XP vem de missões e batalhas.
A cada nível da vila, desbloqueie novas estruturas (árvore de desbloqueio em
balance.json) e libere a melhoria das estruturas até o nível atual da vila.
Melhorar estruturas desbloqueia equipamentos e comidas melhores (ex.: Cozinha
nv.2 libera novos pratos; Ferraria nv.2 libera armas de ferro). Integre o ciclo
completo da vila (trabalho → recursos → construção → cozinha → venda → missões →
evolução) e crie um balanceamento inicial em balance.json. Adicione botão de
reset/save e polimento da navegação por toque. Relate o que precisa de ajuste.
```

---

## 🟠 FASE 2 — FABRICAÇÃO & EQUIPAMENTO (5 etapas)

### Etapa 2.1 — Ferraria: armas e armaduras
**O que será feito:**
- Receitas de armas (machado, espada, lança, arco, cajado) e armaduras (couro, ferro, mithril) em níveis de qualidade.
- **Gates**: armas/armaduras melhores exigem melhorar a Ferraria (que exige nível da vila).
- Materiais consumidos (madeira, minério, ouro); fila de produção.

**🎨 Sprite hook:** sprites de armas/armaduras (🟡7).

**Prompt 2.1:**
```
Implemente js/crafting.js com a ferraria: receitas de armas (machado, espada,
lanca, arco, cajado — dano e tipo) e armaduras (couro, ferro, mithril — defesa e
bônus de HP). Receitas consomem madeira/minério/ouro, com níveis de qualidade
(comum, boa, rara). Armas/armaduras melhores ficam bloqueadas atrás do nível da
Ferraria (que exige nível da vila). UI de fabricação com fila e tempo. Itens vão
para o inventário e podem ser equipados.
```

---

### Etapa 2.2 — Equipar goblins (loadout)
**O que será feito:** cada goblin equipa 1 arma + 1 armadura + 1 runa + 1 talismã; atributos efetivos somam bônus; **overlay** da arma sobre o goblin.

**Prompt 2.2:**
```
Implemente o loadout do goblin: equipar 1 arma, 1 armadura, 1 runa e 1 talismã.
Atributos efetivos somam os bônus dos equipamentos. UI de equipar por toque.
Mostre ataque/defesa resultantes no painel do goblin. Mantenha slots de runa e
talismã vazios (chegam na próxima etapa).
```

---

### Etapa 2.3 — Altar: runas, talismãs, encantamentos e magias
**O que será feito:**
- Runas (bônus de atributo), Talismãs (passivos), Encantamentos (melhoram arma/armadura), Magias (ativas com MP).
- **Gates** pelo nível do Altar (exige nível da vila).
- Definição visual de overlay de equipamento.

**🎨 Sprite hook:** ícones de runas/talismãs/encantamentos (🟡8).

**Prompt 2.3:**
```
Implemente o Altar com: runas (bônus direto de atributo), talismãs (passivos,
ex.: +10% cura, +5% crítico), encantamentos (aplicados a arma/armadura para
melhorá-la) e magias (habilidades ativas com custo de MP: Bola de Fogo, Cura,
Relâmpago, Escudo). Itens melhores bloqueados pelo nível do Altar. Defina o
visual de overlay: armas sobre a mão do goblin, armaduras como tintura/peitoral.
Telas de fabricação e aplicação de encantamento.
```

---

### Etapa 2.4 — Integração e teste de crafting
**O que será feito:** fechar o fluxo minério → forja → encanto → equipar → atributos; revisar custos.

**Prompt 2.4:**
```
Integre o fluxo completo de fabricação: recursos → ferraria (armas/armaduras) →
altar (runas/talismãs/encantamentos/magias) → equipar → atributos efetivos.
Confirme que os gates de nível (vila → estrutura → item) funcionam. Adicione
encantamento melhorando item existente. Revise custos no balance.json e relate o
estado do fluxo.
```

---

### Etapa 2.5 — Bazar: trocar goblins
**O que será feito:**
- Estrutura **Bazar** (desbloqueada em certo nível da vila): gastando **ouro**, você **doa** um goblin e escolhe **1 entre 3** candidatos de **nível equivalente** ao doado.
- Candidatos com status/classes variados; usa o mesmo **sorte crescente** do recrutamento.
- O goblin doado sai da vila (libera a casa para um novo recruta).
- **Melhorar o Bazar** reduz o custo e melhora a qualidade dos candidatos.

**🎨 Sprite hook:** `building_bazaar_1.png` (🟠5).

**Prompt 2.5:**
```
Implemente js/bazaar.js com a estrutura Bazar (desbloqueio por nível da vila em
balance.json): pagando ouro, o jogador doa um goblin e recebe 3 candidatos de
NÍVEL EQUIVALENTE ao doado para escolher 1. Use o mesmo sistema de sorte
crescente do recrutamento (chance de raros aumenta com o total de goblins já
recrutados). O goblin doado é removido da vila e libera sua casa. Melhorar o
Bazar reduz o custo da doação e melhora a qualidade dos candidatos. UI por
toque: selecionar goblin a doar → pagar → escolher entre 3. Custos e fatores em
balance.json.
```

---

## 🔴 FASE 3 — COMBATE POR TURNOS (5 etapas)

### Etapa 3.1 — Batalha básica: turnos e ações
**O que será feito:** tela de batalha (**time de até 4 goblins** vs. inimigos — a vila pode ter mais goblins, mas só 4 entram; seleção de equipe antes da batalha); ordem por velocidade; ações Atacar / Defender / Fugir / Usar item; fórmula de dano e acerto.

**🎨 Sprite hook:** sprites de inimigos (🟠6) — funciona com placeholders.

**Prompt 3.1:**
```
Implemente js/battle.js: combate por turnos entre um time de ATÉ 4 goblins
escolhidos pelo jogador (a vila pode ter mais goblins; crie a tela de seleção de
equipe antes da batalha) e inimigos. Ordem de turno pela velocidade. Ações: Atacar (dano físico por
poderDestrutivo e arma), Defender, Fugir e Usar item (comida/poção cura).
Chance de acerto = precisão do atacante vs velocidade do alvo; crítico pela
precisão. HP/MP, barra de turnos, log de batalha, vitória/derrota. UI por toque.
```

---

### Etapa 3.2 — Habilidades e magias na batalha
**O que será feito:** ação Magia (usa magias equipadas, custa MP, dano pelo Potencial Mágico); Cura (Curandeiro cura +); buffs.

**Prompt 3.2:**
```
Adicione à batalha a ação de magia: usa magias equipadas (custa MP), dano/efeito
pelo potencialMagico. Implemente Cura (healer cura mais), Bola de Fogo, Relâmpago,
Escudo e buffs simples. Mostre MP, cooldowns e efeitos visuais placeholder.
```

---

### Etapa 3.3 — IA inimiga + variedade de armas/agilidades
**O que será feito:** IA simples (escolher alvo, habilidade, curar com HP baixo); armas com comportamentos distintos; habilidades por especialidade.

**Prompt 3.3:**
```
Implemente IA inimiga simples: escolher alvo (mais frágil/perigoso), usar
habilidade quando vantajoso, curar-se com HP baixo. Diferencie armas: espada
(1 alvo, dano alto), lança (2 alvos), arco (age antes na rodada), cajado
(regenera MP). Habilidades por especialidade (guerreiro: golpe pesado; mago:
explosão; curandeiro: cura em área).
```

---

### Etapa 3.4 — XP de goblin + recompensas de batalha (ouro + XP da vila)
**O que será feito:**
- XP por batalha (multiplicado pelo Potencial de Evolução) → nível do goblin.
- **Batalhas dão ouro + XP da vila** além do XP dos goblins.

**Prompt 3.4:**
```
Implemente progressão: XP por inimigo derrotado/batalha vencida, multiplicado
pelo potencialEvolucao do goblin. Ao subir de nível, aumento de atributos e
melhorias de especialidade (animação de level up). Além do XP dos goblins, cada
batalha vencida recompensa ouro + XP da vila (valores em balance.json, escalando
com o nível da fase).
```

---

### Etapa 3.5 — Fase 1 completa + chefe (item especial) + baú (vertical slice)
**O que será feito:**
- 1ª fase completa: 2–3 batalhas comuns + **chefe com mecânica própria**.
- Ao vencer o chefe: **item especial do chefe** (único).
- Concluir a fase (1ª vez): **baú com prêmios** (recursos/itens/receita).
- Recompensas: ouro + XP da vila + XP dos goblins.
- **Este é o vertical slice: o jogo inteiro em miniatura.** 🎉

**🎨 Sprite hook:** chefe (🟠6), item do chefe (🟠6), baú (🔴3), efeitos (🟢10).

**Prompt 3.5:**
```
Monte a fase 1 como vertical slice: sequência de batalhas comuns e uma batalha
de chefe com mecânica única (ex.: invoca ajudantes ou carrega ataque forte com
aviso). Ao vencer o chefe: recompensas (ouro, XP da vila, XP dos goblins) + item
especial único do chefe. Ao concluir a fase pela primeira vez: baú com prêmios
(recursos/itens/receita). Crie js/campaign.js para receber mais fases depois.
Teste o fluxo vila → preparar → batalhar → recompensa.
```

---

## 🔵 FASE 4 — CAMPANHA & PROGRESSÃO (5 etapas)

### Etapa 4.1 — Mapa: consertar e evoluir para liberar vilas
**O que será feito:**
- Mapa-múndi com fases (vilas de goblins inimigas) em sequência.
- **Após a 1ª fase**: para ir à próxima vila, é preciso **consertar o Mapa** (custo de recursos) e **evoluí-lo** para liberar fases seguintes.
- Cada fase = 1 vila inimiga temática com chefe no final.

**🎨 Sprite hook:** `misc_map_1.png` + ícones de vila (🟢9).

**Prompt 4.1:**
```
Crie js/map.js com o mapa de campanha: fases em sequência, cada uma uma vila de
goblins inimiga temática (floresta, mina, pântano, gelo, vulcão). Após vencer a
fase 1, a próxima vila exige consertar o Mapa (custo de recursos/ouro); o Mapa
tem níveis e evoluí-lo libera as fases seguintes. Mostre progresso, fases
bloqueadas e chefes. Navegação por toque e progresso salvo.
```

---

### Etapa 4.2 — Porto e Barqueiro (comerciante itinerante)
**O que será feito:**
- Construir o **Porto** (desbloqueado no nível da vila correspondente) libera o **Barqueiro**.
- O Barqueiro fica **vindo e voltando** com itens à venda (estoque rotativo, com itens raros às vezes).
- Vender/comprar com o Barqueiro (preços próprios, diferentes do Mercado).

**🎨 Sprite hook:** `building_port_1.png`, `misc_boat.png`, ícones de itens (🟢9/🟡8).

**Prompt 4.2:**
```
Implemente js/trader.js com o Porto e o Barqueiro: construir o Porto (nível da
vila exigido em balance.json) libera o Barqueiro, que chega e parte periodicamente
com um estoque rotativo de itens à venda (às vezes raros). UI do Barqueiro com
comprar/vender a preços próprios. Mostre o tempo até a próxima chegada do barco.
```

---

### Etapa 4.3 — Baús de fase + itens especiais de chefe
**O que será feito:**
- Cada fase, na **primeira** conclusão, dá um **baú** com prêmios (recursos, itens, receitas).
- **Toda** batalha de chefe dá um **item especial do chefe** (único, colecionável, com bônus).
- Recompensas padrão de batalha/fase: ouro + XP da vila + XP dos goblins.

**🎨 Sprite hook:** baú (🔴3) + itens de chefe (🟠6).

**Prompt 4.3:**
```
Implemente o sistema de recompensas de fase: baú concedido apenas na PRIMEIRA
conclusão de cada fase (recursos, itens, receitas raras) e item especial único
de cada chefe (colecionável, com bônus/efeito próprio). Recompensas padrão:
ouro + XP da vila + XP dos goblins, escalando com a fase. Mostre as telas de
recompensa (baú, item do chefe, resumo de ouro/XP).
```

---

### Etapa 4.4 — Repetir fases (farm)
**O que será feito:**
- Fases já concluídas podem ser **repetidas**: dão **ouro + XP**, mas **não** dão mais os baús (nem o item do chefe novamente).

**Prompt 4.4:**
```
Implemente a repetição de fases: qualquer fase já concluída pode ser jogada
novamente, rendendo ouro + XP (vila e goblins), mas sem repetir os baús de fase
nem o item especial do chefe. Mostre claramente na UI quais recompensas são de
primeira conclusão e quais são de repetição.
```

---

### Etapa 4.5 — Condições de vitória/derrota + game over
**O que será feito:**
- Vitória: concluir todas as fases (derrotar o chefe final).
- Derrota: todos os goblins nocauteados e sem recursos para reviver.
- Telas com estatísticas e recomeço.

**Prompt 4.5:**
```
Implemente condições de fim de jogo: derrota quando todos os goblins estiverem
nocauteados e sem recursos para reviver; vitória ao concluir a última fase
(derrotar o chefe final). Telas de vitória e game over com estatísticas
(inimigos derrotados, ouro acumulado, nível da vila, dias passados) e botão de
recomeçar.
```

---

## 🟣 FASE 5 — POLIMENTO & ENTREGA (4 etapas)

### Etapa 5.1 — Integração dos sprites finais
**O que será feito:** substituir todos os placeholders pelos seus PNGs; ajustar offsets, animações, ordem de desenho.

**Prompt 5.1:**
```
Faça a integração final dos sprites: atualize o manifest.json com todos os PNGs
entregues, ajuste offsets, frames de animação e ordem de desenho (z-index) por
categoria. Padronize animações (idle, walk, work, attack, hurt, heal) e remova
qualquer placeholder restante.
```

---

### Etapa 5.2 — Som, partículas e feedback
**O que será feito:** efeitos sonoros (corte, mineração, cura, nível, clique), partículas, vibração sutil.

**Prompt 5.2:**
```
Adicione efeitos sonoros e partículas: faíscas na forja, lascas de madeira,
brilho de cura, impacto de golpes, level up, sons de clique/toque. Feedback
visual/sonoro para acertos, críticos e fugas. Vibração sutil em ações
importantes no mobile, se possível.
```

---

### Etapa 5.3 — Balanceamento final e playtest
**O que será feito:** balanceamento geral (economia, dano, HP, XP, custos, recompensas de missão/batalha) e otimização mobile.

**Prompt 5.3:**
```
Faça uma rodada de balanceamento geral (economia, dano, HP de inimigos, XP da
vila e dos goblins, recompensas de missões e batalhas, custos de melhoria e de
conserto do mapa) e otimização para mobile (limitar draw calls, reutilizar
sprites, reduzir lag de toque e uso de memória). Teste do início ao fim e liste
ajustes para deixar a dificuldade justa.
```

---

### Etapa 5.4 — Empacotamento: PWA (e futuro APK)
**O que será feito:** manifest PWA + service worker (offline), ícones 192/512, splash, fullscreen.

**Prompt 5.4:**
```
Transforme o jogo em PWA: manifest de web app, service worker para cache offline,
ícones 192 e 512, tela de splash e fullscreen em mobile. Teste "Adicionar à tela
inicial" e funcionamento offline.
```

---

## 6. PROGRESSÃO DA VILA (resumo visual)

```
NÍVEL 1 (inicial)  Casa de Construção · Casa de Goblin (1 goblin) · Painel de Missões
         │  XP de missões/batalhas
NÍVEL 2  → Serraria, Fazenda
NÍVEL 3  → Cozinha, Mercado
NÍVEL 4  → Mina (pedra/minério infinitos), Estábulo   (+ plantar árvores)
NÍVEL 5  → Ferraria (armas/armaduras)
NÍVEL 6  → Altar (runas/talismãs/magias/encantamentos), Bazar (trocar goblins)
NÍVEL 7  → Porto (Barqueiro)
NÍVEL 8  → Quartel (expedições/bônus de combate)
...
Melhoria de estrutura: limitada ao nível atual da vila.
Melhorar estrutura: desbloqueia equipamentos e comidas melhores.
```

*(Árvore de desbloqueio completa e níveis máximos ficam em `balance.json` — ajustável.)*

---

## 7. CHECKLIST DE PRIORIDADE (resumo)

- [ ] **F0** Base + loop mobile → loader/i18n/save
- [ ] **F1** Goblins+habitação (escolher 1 de 3) → recursos/nós finitos → trabalho → cozinha → construção (Casa de Construção) → mercado → missões → XP/nível da vila
- [ ] **F2** Ferraria → equipar → altar → integração (gates de nível) → Bazar (trocar goblins)
- [ ] **F3** Batalha → magias → IA/armas → XP+recompensas → **vertical slice: fase 1 + chefe (item especial) + baú**
- [ ] **F4** Mapa (consertar/evoluir) → Porto/Barqueiro → baús/itens de chefe → repetir fases → vitória/derrota
- [ ] **F5** Sprites finais → som/partículas → balanceamento → PWA/APK

**Regra de ouro:** cada Etapa termina **jogável e visível**. Você desenha em paralelo (siga a ordem de prioridade dos sprites) e solta os PNGs na pasta conforme termina.

---

## 8. BALANCEAMENTO INICIAL (ponto de partida — tudo em `balance.json`)

| Item | Valor inicial |
|---|---|
| **Início da vila** | Casa de Construção (nv.1) · 1 Casa de Goblin (1 goblin) · Painel de Missões (nv.1) |
| Atributos iniciais do goblin | 3–7 (aleatório) |
| Nível máximo (goblin / vila) | 30 / 20 (ajustável) |
| HP | 20 + (vitalidade × 10) |
| MP | 10 + (potencialMágico × 5) |
| Dano físico | (força × 2) + dano da arma − defesa do alvo |
| Dano mágico | (magia × 2,2) + poder da magia − resistência |
| Chance de acerto | 80% + (precisão atacante − velocidade alvo) × 2 |
| Chance de crítico | 5% + precisão × 0,5% |
| Ordem de turno | maior velocidade age primeiro |
| XP do goblin | 10 × nível do inimigo × (1 + potencialEvolucao × 0,05) |
| **XP da vila** | missões 20–100 · batalha 30 + 10×nível da fase · chefe +50 |
| XP para nível N (vila) | 100 × N^1,6 |
| Corte de árvore / quebra de pedra | 1 unidade a cada 8s (força reduz o tempo) |
| Nós naturais | árvore: 10 madeiras · pedra: 10 pedras (esgotam) |
| Preços | madeira 2 · pedra 2 · minério 5 · comida 3–15 ouro |
| Casa de Goblin | 15 madeira + 10 pedra → construir/melhorar abre recrutamento (escolher 1 de 3) |
| Batalha | time de até **4 goblins** (a vila pode ter mais) |
| Sorte de recrutamento | +0,5% de chance rara por goblin já recrutado (ajustável) |
| Bazar | doar goblin: 50 ouro × nível do goblin → escolher 1 entre 3 de nível equivalente |
| Melhoria de estrutura | limitada ao nível da vila; custo cresce por nível |
| Conserto do Mapa (1ª vez) | 30 madeira + 30 pedra + 100 ouro (cresce a cada vila) |
| Repetir fase | ouro + XP (sem baú e sem item de chefe) |

---

## 9. GLOSSÁRIO BILÍNGUE (base do i18n)

| PT-BR | EN |
|---|---|
| Poder Destrutivo | Destructive Power |
| Potencial Mágico | Magic Potential |
| Vitalidade | Vitality |
| Velocidade | Speed |
| Precisão | Precision |
| Potencial de Evolução | Evolution Potential |
| XP da Vila | Village XP |
| Nível da Vila | Village Level |
| Casa de Construção | Construction House |
| Casa de Goblin | Goblin House |
| Painel de Missões | Quest Board |
| Missão | Quest |
| Baú | Chest |
| Item do Chefe | Boss Item |
| Mapa | Map |
| Consertar Mapa | Repair Map |
| Porto | Port |
| Barqueiro | Boatman |
| Árvore / Pedra | Tree / Rock |
| Mina / Plantar árvores | Mine / Plant trees |
| Serraria / Fazenda / Cozinha | Sawmill / Farm / Kitchen |
| Ferraria / Estábulo / Altar / Quartel | Blacksmith / Stable / Altar / Barracks |
| Melhorar estrutura | Upgrade building |
| Repetir fase | Replay stage |
| Bazar | Bazaar |
| Recrutar / Doar goblin | Recruit / Donate goblin |
| Escolher entre 3 | Choose one of three |
| Time de batalha (até 4) | Battle party (up to 4) |
| Cortar / Minerar / Plantar | Chop / Mine / Farm |
| Atacar / Defender / Fugir | Attack / Defend / Flee |

---

## 📒 LOG DE DESENVOLVIMENTO (etapas concluídas)

| Etapa | Status | Prévias (`/home/user/previas/`) |
|---|---|---|
| 0.1 Base + loop | ✅ | — |
| 0.2 Loader/i18n/save | ✅ | — |
| 0.3 Ilha + câmera + sprites goblin | ✅ | `teste-ilha.png` |
| 1.1 Goblins + habitação + recrutamento 1-de-3 | ✅ | `etapa-1-1-mundo.png`, `etapa-1-1-construcao.png`, `etapa-1-1-recrutamento.png`, `etapa-1-1-roster.png` |
| 1.2 Recursos finitos + HUD | ✅ | `etapa-1-2-floresta.png`, `etapa-1-2-trabalho.png`, `etapa-1-2-esgotado.png` |
| 1.3 Trabalho (cortar/minerar) + progresso | ✅ | `etapa-1-3-trabalho.png`, `etapa-1-3-hud.png` |
| UI de construção rústica (botão de canto + abas) | ✅ | `etapa-build-ui-mundo.png`, `etapa-build-ui-painel.png`, `etapa-build-ui-melhorias.png` |
| Mudança p/ paisagem 640×360 + re-layout de todas as telas | ✅ | `etapa-paisagem-mundo.png`, `etapa-paisagem-build.png`, `etapa-paisagem-recrutamento.png`, `etapa-paisagem-roster.png` |
| Recuperação do projeto-fonte (o repo só tinha o build) | ✅ | — |
| 1.8 XP e nível da vila + desbloqueios | ✅ | (testes automatizados) |
| 1.5 Construção de TODAS as estruturas + melhorias | ✅ | (testes automatizados) |
| 1.7 Painel de Missões | ✅ | (testes automatizados) |
| 1.4 Cozinha: comida que cura | ✅ | (testes automatizados) |
| Fazenda e Mina como postos de trabalho infinitos | ✅ | (testes automatizados) |

**Notas da UI de construção:** botão rústico "Construir" no canto inferior esquerdo abre o painel da Casa de Construção em qualquer lugar do mapa (estilo inspirado na referência do usuário: painel de pranchas com pregos/lascas, placa de título, abas, cards de pergaminho com ícone brilhando, contagem construída e custo com ícones). Aba **Estruturas**: catálogo `BUILD_DEFS` — casas + futuras estruturas travadas por nível da vila (Serraria/Fazenda nv2 … Quartel nv8) mostradas com placa "?" + "Vila nv X"; slot "…em breve…". Aba **Melhorias**: melhorar casas (+1 capacidade). Tocar fora do painel fecha. Novas estruturas implementadas futuramente **aparecem automaticamente nesse catálogo**.

**Notas da 1.2:** `nodes.js`: 90 árvores (15 madeira cada) + 55 pedras (12 pedra cada) espalhadas na grama fora da clareira, distância mínima 26px; estoque esgota → toco/entulho (`node_tree_stump`, `node_rock_rubble`); barra de estoque sobre o nó; toque no nó envia o goblin livre mais próximo; estado dos nós persistido no save. HUD com 5 recursos (madeira, pedra, minério, comida, ouro) com ícones reais (`res_food` = coxa de carne).

**Notas da 1.3:** ciclo de trabalho acelerado por `velocidade` + `poderDestrutivo` (mul 0.4–1.0); especialidade `worker` tem 35% de chance de rendimento dobrado; barra de progresso do ciclo sobre o goblin trabalhando; animação `attack` como animação de trabalho; tocar no goblin trabalhando chama ele de volta; textos flutuantes "+1 madeira"; preparado para fontes renováveis (mina/plantio) em etapas futuras. Desvio do plano: atribuição é por toque no NÓ (mobile-friendly), não goblin→posto.

**Notas da 1.1:** `goblin.js` (entidade: 6 atributos, especialidade, raridade, nível/XP com bônus de potencialEvolucao), `village.js` (recursos iniciais 50 madeira/30 pedra/100 ouro; Casa de Construção + Casa de Goblin + Painel de Missões iniciais; construir casa 15m+10p; melhorar casa 25m+15p ×1.6/nível, máx 3; capacidade = soma dos níveis das casas; construir/melhorar abre escolha de 1 entre 3 candidatos com sorte crescente de +0,5%/recrutado), `ui.js` (UI imediata no canvas), telas: mundo / construção / recrutamento / roster / detalhe. Arte real (sem placeholder): 3 prédios + 4 recursos + 2 nós em pixel art autoral 32×32.

**Notas da recuperação do projeto-fonte:** o repositório havia ficado só com o build de arquivo único (`vila-de-goblins-jogavel.html`) — a árvore `js/`, `css/` e `assets/` tinha se perdido. `tools/unbuild.py` faz o caminho inverso do build e recupera tudo (13 módulos, 74 sprites, JSONs, CSS); `tools/build_singlefile.py` refaz o arquivo único. O ciclo fonte → build → fonte é fiel (conferido sprite a sprite e módulo a módulo).

**Notas da 1.8 (XP/nível da vila):** `village.level` era **fixo em 1** — nenhuma estrutura além de casas podia ser construída, e o catálogo mostrava tudo travado. Agora: `xpNext() = 100 × N^1.6` (§8), `gainXp()` acumula e sobe vários níveis de uma vez, teto em `maxLevel` (20). XP vem das missões (batalhas entram na Fase 3). Cada nível libera estruturas (`unlockedAt`) e **eleva o teto de melhoria** de todas elas (`maxUpgradeLevel` = nível da vila, §2.5). HUD ganhou nível + barra de XP; ao subir aparece o banner "VILA NÍVEL N!" e um aviso do que foi desbloqueado.

**Notas da 1.5 (construção completa):** o catálogo `BUILDINGS` mora agora no `village.js` (fonte única): sprite, nível exigido, quantidade máxima, teto de melhoria e custo de cada uma das 12 estruturas. `build(type)` vale para todas; `blockedReason(type)` responde **por que** não dá (`level` / `count` / `cost`) e a UI mostra a mensagem certa em vez de um "recursos insuficientes" genérico. Catálogo paginado (6 por página) mostrando as 12; estrutura única já construída ganha selo "✔ construída". Aba **Melhorias** agora lista casas **e** as demais estruturas, marcando o que está travado pelo nível da vila. Posições fixas no anel da clareira (`STRUCT_SLOTS`).

**Notas da 1.7 (missões):** `quests.js` com 3 slots fixos; cada missão pede recursos ou pratos e paga **ouro + XP da vila**. Dificuldade escala ~12% por nível da vila e o que pode ser pedido tem gate por nível (minério só a partir do nv4, pratos a partir do nv3). Recompensa proporcional ao valor pedido, XP limitado a 20–100 (§8). Slot entregue entra em renovação (45s) e volta sozinho. Botão "Missões" no mundo mostra um selo verde com quantas dá para entregar agora.

**Notas da 1.4 (cozinha):** `cooking.js` com 4 receitas — pão, sopa (Cozinha nv1), ensopado (nv2), banquete (nv3): **melhorar a Cozinha desbloqueia pratos melhores**, como manda o §2.5. Consomem `food` (da Fazenda) e produzem pratos que curam HP fora de batalha e servem de moeda nas missões. Goblin com especialidade `cook` tem chance de render porção dobrada. Tela da Cozinha: receitas com custo/cura, despensa e cura por toque (escolhe o prato → toca no goblin ferido).

**Notas da Fazenda/Mina (§2.6):** as duas viram **postos de trabalho infinitos** (`nodes.syncFacilities`), reaproveitando o mesmo sistema de trabalho dos nós naturais — o goblin caminha até lá e produz em ciclos. Fazenda → comida; Mina → pedra com chance crescente de minério conforme o nível. A Serraria aumenta o rendimento de madeira dos nós de árvore. Postos infinitos não são salvos: nascem das estruturas no boot.

**Testes (`bash tools/test.sh`):** o Playwright não instala neste ambiente (sem binário de navegador e download bloqueado), então as prévias PNG deram lugar a **151 testes automatizados** em 4 suítes: `smoke` (lógica), `render` (as 6 telas desenham, traduções e sprites conferidos), `playthrough` (uma partida inteira: nv1 → nv3 desbloqueando e cozinhando) e `build` (o arquivo único distribuído sobe sozinho). O `playthrough` é o que pega "o jogo trava no meio" — exatamente o problema que o nível fixo causava.

---

## ✅ PRÓXIMO PASSO SUGERIDO

O ciclo da **Fase 1 está fechado**: coletar → construir → missões → XP → subir de nível → desbloquear → cozinhar → curar.

Próxima etapa natural: **1.6 — Mercado** (vender comida/recursos por ouro e comprar o que falta), que fecha a economia antes da Fase 2 (Ferraria/equipamentos). Alternativa: pular direto para a **Fase 3 — Combate por turnos**, já que os goblins têm os 6 atributos, HP/MP e comida curativa prontos.
