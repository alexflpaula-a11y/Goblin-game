# 🧌 Vila de Goblins

[![Testes](https://github.com/alexflpaula-a11y/Goblin-game/actions/workflows/ci.yml/badge.svg)](https://github.com/alexflpaula-a11y/Goblin-game/actions/workflows/ci.yml)
[![Jogar online](https://img.shields.io/badge/jogar-online-2ea44f?logo=itch.io&logoColor=white)](https://alexflpaula-a11y.github.io/Goblin-game/)
[![Licença: MIT](https://img.shields.io/badge/licença-MIT-blue.svg)](LICENSE)

Jogo mobile-first de **gerenciamento de vila + batalhas por turnos**, em HTML5 Canvas + JavaScript puro (sem dependências). Você controla uma vila de goblins: corte madeira, colete pedras, erga divindades, cumpra missões, cozinhe, recrute goblins (escolhendo 1 entre 3, com **45 variações visuais**) e — nas próximas fases — invada outras vilas.

> ### 🎮 [**Clique aqui para jogar agora →**](https://alexflpaula-a11y.github.io/Goblin-game/)
> A raiz publicada serve a versão de arquivo único (carrega num toque, funciona offline). O GitHub Pages republica sozinho a cada push na `main`.

## 📑 Índice

- [▶️ Como jogar](#️-como-jogar)
- [🔄 O ciclo do jogo](#-o-ciclo-do-jogo)
- [🏚️ Armazém, inventário e equipamento](#️-armazém-inventário-e-equipamento)
- [🗂️ Estrutura do projeto](#️-estrutura-do-projeto)
- [🤖 Automação (CI/CD)](#-automação-cicd)
- [🔧 Ferramentas](#-ferramentas)
- [✅ Testes](#-testes)
- [🎨 Sprites](#-sprites)
- [🌐 Idiomas](#-idiomas)
- [💾 Salvamento](#-salvamento)
- [📜 Status](#-status)

## ▶️ Como jogar

**🎮 Jogar online (GitHub Pages):** **<https://alexflpaula-a11y.github.io/Goblin-game/>**
A raiz redireciona para a **versão de arquivo único** (carrega num toque, funciona offline). Link direto do arquivo:
**<https://alexflpaula-a11y.github.io/Goblin-game/vila-de-goblins-jogavel.html>**

**Sem instalar nada:** abra `vila-de-goblins-jogavel.html` no navegador (PC ou celular). É um build de arquivo único com sprites e textos embutidos — funciona offline.

**Modo desenvolvimento:** sirva a pasta e abra `http://localhost:8080/index-dev.html`
(o `index-dev.html` carrega os módulos de `js/` por HTTP; o `index.html` da raiz é só o redirecionamento para o build):

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
| Toque numa divindade | envia/retira um goblin para ativar o culto |
| Construir → toque no mapa | escolhe exatamente onde colocar a estrutura |
| Botão ↔ → estrutura → mapa | move qualquer estrutura já construída |
| Toque nos outros prédios | abre a tela correspondente |
| Botões no rodapé | **Construir**, **Mover**, **Área dos Goblins**, **Missões**, **Cozinha**, **Mercado**, **Armazém**, **Vila** |
| Área dos Goblins | defina cada goblin como **Livre**, **Madeira**, **Pedra** ou **Comida**; ele busca o próximo posto disponível automaticamente |

## 🔄 O ciclo do jogo

```
coletar recursos → construir → cumprir missões → XP da vila
   → subir de nível → desbloquear estruturas → fazenda/cozinha
   → curar goblins → vender o excedente no mercado → repetir
```

A **vila sobe de nível** com o XP das missões. Cada nível libera novas estruturas *e* eleva o teto de melhoria de todas elas. Melhorar a Cozinha, por exemplo, desbloqueia pratos melhores.

### Obras

Colocar ou melhorar uma estrutura cria uma **lona branca cercada**. Um goblin livre vai até ela, trabalha levantando poeira e o cronômetro só avança enquanto ele está na obra. A duração segue o nível de desbloqueio da estrutura: casas (nível 1) levam **10 / 20 / 30 s** nos níveis 1–3; estruturas desbloqueadas no nível 2 levam **20 / 30 / 40 s**; as do nível 3 levam **30 / 40 / 50 s**, e assim sucessivamente. Quando acabar, a lona brilha: toque nela para recolher a construção pronta.

| Nível | Desbloqueia |
|---|---|
| 1 | Casa de Construção · Casa de Goblin · Painel de Missões |
| 2 | Serraria · Fazenda · **Armazém** |
| 3 | Cozinha · Mercado · **Grande Árvore** · **Golem de Pedra** |
| 4 | Estábulo |
| 5 | Ferraria |
| 6 | Altar · Bazar |
| 7 | Porto |
| 8 | Quartel |

No nível 3, a **Grande Árvore** canta e faz árvores brotarem do chão, enquanto o **Golem de Pedra** cria e arremessa rochas rúnicas que caem e permanecem coletáveis na ilha. As divindades começam vazias: toque nelas para enviar um goblin livre e iniciar o culto; toque novamente para liberá-lo. A ilha nunca ultrapassa **40 árvores e 40 pedras no total**, e os novos recursos divinos só surgem longe das estruturas.

## 🏚️ Armazém, inventário e equipamento

O **Armazém** (vila nv 2) guarda tudo e abre o inventário da vila:

- **Recursos** — madeira, pedra, minério, comida e ouro, mais a **despensa** de pratos cozinhados;
- **Itens** — área separada com os equipamentos em **espaços** (slots), um item por célula. A capacidade cresce com o nível do Armazém (nv1 = 16, nv2 = 24, nv3 = 32 espaços).

Os equipamentos são comprados no **Mercado** (agora em quantidade, limitados pelos espaços do Armazém) e ainda **não têm status** — isso chega com as batalhas. Cada goblin tem a própria tela de equipar, com **10 espaços rodando o personagem**: capacete, peitoral, botas, calça, **2 anéis**, arma primária, arma secundária, runa e colar. Tocar num espaço lista os itens do tipo guardados no armazém (equipar troca a peça e devolve a antiga).

A mesma interface ainda tem duas abas: **Alimentos** (escolher um prato e alimentar qualquer goblin) e **Habilidades** (2 espaços por goblin; cada um usa as habilidades da própria especialidade + as genéricas).

As peças **Avaritia** (capacete/peitoral/calça) continuam mudando o sprite do goblin que as veste — combinações individuais → pares → conjunto completo — e o **peitoral de ferro** tem a própria skin. As características físicas de cada goblin são preservadas sob a armadura por overlays compostos em tempo de execução. Item equipado fica no corpo do goblin (sai do armazém) e pode ser passado para outro goblin a qualquer momento.

## 🗂️ Estrutura do projeto

```
index.html          redireciona para o build (é o que o GitHub Pages serve na raiz)
index-dev.html      versão de desenvolvimento (carrega js/ por HTTP)
vila-de-goblins-jogavel.html   build de arquivo único (é o que se distribui)

css/style.css       HUD e layout DOM
js/
  loader.js         mini sistema de módulos (dev e build usam a mesma API)
  main.js           boot, game loop, roteamento de telas
  config.js         resolução lógica 640×360 (paisagem) e constantes
  input.js          gestos multi-toque (pan/pinch/tap) + mouse
  camera.js         câmera livre com clamp na ilha
  world.js          ilha procedural + goblins que passeiam/trabalham
  nodes.js          nós naturais + árvores/rochas divinas renováveis
  deities.js        cantos, arremessos, acólitos e limite dos milagres
  village.js        recursos, catálogo de estruturas, XP/nível da vila
  goblin.js         entidade: 6 atributos, especialidade, raridade, XP
  quests.js         painel de missões (itens → ouro + XP da vila)
  cooking.js        receitas, pratos que curam
  market.js         mercado: vender e comprar por ouro
  inventory.js      armazém: catálogo de itens, espaços, equipar/desequipar
  abilities.js      catálogo de habilidades (2 espaços por goblin)
  gear.js           sprites do goblin conforme o que ELE vestiu (Avaritia/ferro)
  ui.js             UI imediata no canvas + visual rústico goblin
  assetLoader.js    sprites reais ou placeholder automático
  i18n.js           PT-BR / EN em tempo real
  save.js           localStorage + autosave (desativado no dev — `SAVE_ENABLED`)
  balance.js        carrega o balance.json
assets/
  data/             balance.json, i18n.pt-br.json, i18n.en.json
  manifest.json     lista de sprites (nomes lógicos → caminhos)
  sprites/          PNGs por categoria (inclui divindades 64×64 geradas por IA)
tools/              build, testes e geração de sprites
docs/               documentação
  planejamento-jogo-gnomos.md  planejamento completo + log de desenvolvimento
  rascunho-inicial.md          primeiro rascunho do projeto (arquivo histórico)
art-source/         arte-fonte do autor (NÃO carregada em runtime)
  goblins/          os 45 GIFs de variação usados por gen_goblin_variations.py
  avaritia/         sprite sheet / gif / zip / preview do conjunto Avaritia
  peitoral-ferro/   sprite sheet / zip / preview do peitoral de ferro
  misc/             imagens e sprites avulsos de referência
.github/workflows/  automação (testes + deploy no GitHub Pages)
```

## 🤖 Automação (CI/CD)

- **Testes automáticos** — o fluxo `.github/workflows/ci.yml` roda as 7 suítes (`bash tools/test.sh`) em cada Pull Request e em pushes para a `main`, bloqueando merges que quebrem algo. O status aparece no badge no topo.
- **Publicação automática** — o GitHub Pages republica sozinho a cada push na `main`. A raiz `index.html` apenas **redireciona para `vila-de-goblins-jogavel.html`** (o build de arquivo único), então o link online sempre carrega a versão rápida — sem milhares de pedidos de sprite da versão de desenvolvimento.

> **Fluxo recomendado:** trabalhe numa branch → abra um PR (o CI roda os testes) → depois de aprovado, dê merge na `main`. Lembre-se de rodar `python3 tools/build_singlefile.py` e commitar o `vila-de-goblins-jogavel.html` sempre que mexer em `js/`, `css/` ou `assets/`.

## 🔧 Ferramentas

```bash
python3 tools/build_singlefile.py          # gera o vila-de-goblins-jogavel.html
python3 tools/gen_sprites.py               # (re)gera a pixel art de prédios e comidas
python3 tools/gen_icons.py                 # (re)gera ícones 16×16 de itens/habilidades
python3 tools/gen_goblin_variations.py     # extrai as 45 variações em lotes de 5
python3 tools/unbuild.py            # extrai a fonte de volta a partir do build
bash    tools/test.sh               # roda as 7 suítes de teste
```

> **Importante:** depois de mexer em `js/`, `css/` ou `assets/`, rode o
> `build_singlefile.py` — senão o arquivo jogável fica para trás.

## ✅ Testes

370 testes automatizados, sem navegador (`bash tools/test.sh`):

| Suíte | O que cobre |
|---|---|
| `smoke` | lógica pura: vila, goblins, missões, cozinha, inventário, habilidades, save |
| `render` | as telas desenham sem erro; traduções e sprites conferidos |
| `playthrough` | uma partida inteira — o ciclo do jogo fecha do início ao fim |
| `gear` | armazém: prateleira, capacidade, equipar por goblin, skins, migração de save |
| `tap` | toques reais (input → routeTap → render): equipar, alimentar, habilidades |
| `boot` | boot real: saves desativados, save velho ignorado, estouro 17/16, recrutamento, salto de nível |
| `build` | o arquivo único distribuído sobe sozinho |

## 🎨 Sprites

O conjunto **Avaritia** (peitoral, calça, capacete + 3 pares + conjunto completo, 62 frames cada) vive em `sprites/itens/` e é gerado por `sprites/itens/gerar_item.py` / `gerar_conjunto.py` a partir dos frames do goblin no `window.EMBEDDED` do jogo — apenas recolor de pixels existentes.

PNGs **32×32** referenciados por **nome lógico** no `manifest.json`. Se um PNG não existir, um placeholder é desenhado automaticamente (o jogo nunca quebra). Os goblins têm **45 variações físicas** vindas dos GIFs do autor — dente dourado, tapa-olho, cicatrizes, albinismo, tatuagens e combinações — cada uma com os 62 quadros de `idle/walk/attack/hurt/death`. `tools/gen_goblin_variations.py` extrai todas em **9 lotes de 5** e também gera os overlays que mantêm a variação sob a armadura. Prédios, recursos e comidas são pixel art autoral gerada por `tools/gen_sprites.py`.

## 🌐 Idiomas

PT-BR e EN com troca em tempo real (botão no HUD). Textos em `assets/data/i18n.*.json`.

## 💾 Salvamento

**Desativado durante o desenvolvimento** — o jogo começa uma vila nova a cada
partida e nada é gravado no `localStorage` (qualquer save antigo é descartado
no boot). Quando tudo estiver pronto, basta trocar `SAVE_ENABLED` para `true`
em `js/save.js`; o sistema (save/load/autosave a cada 10s) continua intacto.

## 📜 Status

**Fase 1 concluída (1.1 → 1.8):** ilha + câmera, goblins + habitação + recrutamento 1-de-3, recursos finitos, trabalho, construção de todas as estruturas, missões, XP/nível da vila, cozinha, **Mercado** e as duas divindades renováveis (Grande Árvore e Golem de Pedra).

**Etapa 1.7 — Armazém & Inventário:** o **Armazém** (vila nv 2, melhorável: 16/24/32 espaços) abre o inventário da vila com todos os recursos + despensa numa área e os **itens de equipamento em slots** na outra. 14 equipamentos (sem status por enquanto): conjunto Avaritia (peitoral 120, capacete 150, calça 90 ouro), conjunto de ferro (capacete 45, peitoral 60, calça 40), botas de couro, anel de cobre/rubi, colar de presas, espada, clava, escudo e runa azul. A interface de equipar tem **10 espaços rodando o goblin** (capacete, peitoral, botas, calça, 2 anéis, arma primária, arma secundária, runa, colar) + aba **Alimentos** (alimentar goblins) + aba **Habilidades** (2 espaços por goblin, por especialidade + genéricas). Cada goblin veste o que quiser — as peças Avaritia e o peitoral de ferro mudam o sprite individualmente.

**A seguir:** Fase 2 (Ferraria, Altar, Bazar) → Fase 3 (combate por turnos — quando os equipamentos ganham status). Roadmap completo em [`docs/planejamento-jogo-gnomos.md`](docs/planejamento-jogo-gnomos.md).
