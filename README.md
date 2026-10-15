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
| Toque numa divindade | abre seu Santuário: até 3 acólitos, XP, nível e taxa de produção |
| Construir → toque no mapa | escolhe exatamente onde colocar a estrutura |
| Setinhas ▲ ▼ ◀ ▶ em volta da prévia | empurram a estrutura um pouco em cada direção, para o ajuste fino antes de **Confirmar** |
| Toque longo numa estrutura pronta | **único jeito de mover**: preenche um anel amarelo e, ao completar, libera o novo local |
| Toque nos outros prédios | abre a tela correspondente |
| Botões no rodapé | **Construir**, **Recrutar** (quando há vaga), **Missões**, **Cozinha**, **Mercado**, **Armazém**, **Vila** |
| Vila | concentra a lista de todos os goblins e suas abas **Goblins** e **Trabalhos**; em Trabalhos, arraste somente goblins disponíveis até um ofício e toque no ofício para ver apenas sua equipe atual |
| Cozinha → **Cozinheiros** | designe até **3 cozinheiros** dentre os disponíveis; a fila guarda até **20 receitas** na ordem escolhida, e cada cozinheiro que chega à panela acelera o preparo |

### Modos de jogo

Ao abrir o jogo aparecem dois modos:

- **Modo Normal** — a partida padrão: a ilha começa vazia, os recursos são finitos e as estruturas são liberadas pelo nível da vila.
- **Modo Teste** — para experimentar o jogo inteiro: os recursos são **infinitos** (a barra superior mostra ∞ e nada é descontado), **todas as estruturas já estão desbloqueadas** e o rodapé ganha o botão **☺ Goblins**, uma galeria paginada com **todas as aparências existentes** — escolha qualquer uma e ela entra na vila na hora, sem depender de vagas de moradia.

O modo escolhido vale para a sessão inteira. Para abrir direto no modo Teste (prévias e testes), use `?mode=test` na URL.

### Posicionar e mover estruturas

Mover uma estrutura é sempre o mesmo gesto: **segure o dedo em cima dela** até o anel amarelo fechar. Não existe botão de mover — um toque simples continua abrindo a tela do prédio. Um goblin parado na frente não atrapalha: enquanto o dedo não se mexe, o anel continua enchendo.

Ao construir, ou assim que o anel completa, aparece a prévia translúcida com as quatro **setinhas** em volta. Cada toque numa seta desloca a prévia um pouco naquela direção; o toque no mapa reposiciona a prévia de uma vez. **Confirmar** grava o ponto exato e **Cancelar** desiste.

As construções agora podem ficar **bem mais próximas**. O espaço reservado deixou de ser um círculo largo e passou a ser a **base** do prédio, que é larga e rasa: vizinhas lado a lado precisam de apenas **50 px** entre os centros (quase encostadas) e uma fileira nova cabe **40 px** atrás da anterior — antes a regra exigia 72 px em qualquer direção. A elipse da prévia mostra exatamente esse espaço, e árvores e pedras também passaram a atrapalhar menos (44 px). Como o desenho é ordenado pela profundidade, quem está na frente cobre quem está atrás, e **o toque sempre abre a construção que aparece na frente**.

### Raridade dos goblins

Cada candidato sai com uma das **sete faixas**, e cada faixa tem a sua fração própria: **1/2 comum · 1/5 incomum · 1/10 raro · 1/50 épico · 1/100 mítico · 1/500 lendário · 1/5000 divino**. Essas frações são os pesos do sorteio; normalizadas, dão ≈ 60,08% · 24,03% · 12,02% · 2,40% · 1,20% · 0,24% · 0,02% no começo da partida.

O **denominador nunca muda**, mas o **numerador começa em 1 e sobe 0,1 a cada goblin recrutado** — com 9 goblins na vila as frações estão em 1,9/2 · 1,9/5 · 1,9/10 · 1,9/50 · 1,9/100 · 1,9/500 · 1,9/5000. Quando o numerador alcança o denominador a faixa chega ao **máximo** e sai do sorteio: com 10 goblins o comum fecha em 2/2 e nunca mais aparece, sobrando incomum 2/5, raro 2/10, épico 2/50, mítico 2/100, lendário 2/500 e divino 2/5000. Os pontos de corte são 10 recrutas (comum), 40 (incomum), 90 (raro), 490 (épico), 990 (mítico), 4990 (lendário) e 49990 (divino).

A raridade define a faixa de atributos sorteada, a cor das barras e o número de estrelas: **Mítico** 8–10, **Lendário** 9–10 e **Divino** 10 em tudo, com sete estrelas.

A tabela completa — fração atual, chance real e aviso de faixa esgotada — fica no botão **Chances**, dentro da galeria ☺ Goblins, e **só existe no modo Teste**: é informação de bastidor e não aparece numa partida normal. No modo Teste as obras também ficam prontas na hora e **cada vaga de moradia nova já chega com um goblin sorteado**, para conferir as chances em poucos toques.

## 🔄 O ciclo do jogo

```
coletar recursos → construir → cumprir missões → XP da vila
   → subir de nível → desbloquear estruturas → fazenda/cozinha
   → curar goblins → vender o excedente no mercado → repetir
```

A **vila sobe de nível** com o XP das missões. Cada nível libera novas estruturas *e* eleva o teto de melhoria de todas elas. Melhorar a Cozinha, por exemplo, desbloqueia pratos melhores.

### Fundação da vila

Uma partida nova começa com a ilha **sem prédios e sem goblins**. O primeiro painel pede o local da **Casa de Construção**, que é gratuita. Ela ainda passa pela lona de fabricação, mas como tem duração zero a lona aparece brilhando e basta tocá-la para concluir. Só então o catálogo normal é liberado.

O **Painel de Missões** e as **três primeiras Casas de Goblin** também não custam recursos. Não existem missões antes de o Painel ter sido concluído. A primeira Casa, como a Casa de Construção, tem duração zero mas ainda exige recolher a lona brilhante; ao concluir a Casa, abre-se a escolha do primeiro goblin. A segunda e a terceira Casas continuam sendo obras normais com cronômetro. Cada nível de uma Casa concede mais uma vaga de moradia; durante uma melhoria, as vagas que ela já tinha continuam valendo e, ao recolher a obra pronta, a nova vaga abre o recrutamento. Enquanto existir vaga, o botão **Recrutar** permite reabrir a escolha de candidatos.

### Obras

Colocar ou melhorar uma estrutura cria uma **lona de obra**. A lona aguarda até que o jogador abra **Vila → Trabalhos** e nomeie um goblin como **Construtor**; somente um construtor nomeado vai até ela, trabalha levantando poeira e faz o cronômetro avançar. A duração segue o nível de desbloqueio da estrutura: casas (nível 1) levam **10 / 20 / 30 s** nos níveis 1–3; estruturas desbloqueadas no nível 2 levam **20 / 30 / 40 s**; as do nível 3 levam **30 / 40 / 50 s**, e assim sucessivamente. A **Casa de Construção** também pode ser melhorada: cada nível extra acelera todas as obras em **25%** (esse número só é exibido na lista de melhorias do modo Teste; numa partida normal ele fica de bastidor). Ao acabar — ou imediatamente nas fundações de duração zero — a lona brilha: toque nela para recolher a construção pronta.

### Cozinha e cozinheiros

Abra a **Cozinha** e use a aba **Cozinheiros** para designar até **três** goblins. A aba **Cozinhar** permite organizar uma fila de até **20 pratos**: a ordem da lista define a prioridade, itens podem ser removidos antes de iniciar e os ingredientes só saem do estoque quando o item chega ao começo da fila e a preparação começa. Receitas de cozinha nível 1 levam **10 s**, nível 2 levam **20 s** e nível 3 levam **30 s** com um cozinheiro; cada cozinheiro que já alcançou a panela soma velocidade ao mesmo preparo. A porção entra na despensa apenas ao término.

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

No nível 3, a **Grande Árvore** canta e faz árvores brotarem do chão, enquanto o **Golem de Pedra** cria e arremessa rochas que caem e permanecem coletáveis na ilha. Tocar numa delas abre seu **Santuário**: até **3 goblins** podem louvar ao mesmo tempo. Cada acólito ativo acelera tanto a produção quanto o ganho de XP de louvor; a barra de XP é o único modo de elevar a divindade até o nível 3 — os santuários não entram na loja de melhorias comum. Cada nível torna os ciclos de produção mais rápidos. Por enquanto a Árvore entrega apenas madeira e o Golem apenas **pedra**: materiais especiais e a forja/compra de runas continuam reservados para uma fase futura, sem reabrir slots de runa nos goblins. Uma partida nova nasce com **200 árvores e 200 pedras ativas**. A produção divina respeita esse teto por tipo: quando alguém coleta um nó, a vaga permite outra criação, sem limite vitalício de reposições. Os recursos divinos só surgem longe das estruturas. Tocos e entulho de pedra somem após **10 segundos**, mantendo o terreno limpo.

## 🏚️ Armazém, inventário e equipamento

O **Armazém** (vila nv 2) guarda tudo e abre o inventário da vila:

- **Recursos** — madeira, pedra, minério, comida e ouro, mais a **despensa** de pratos cozinhados;
- **Itens** — área separada com os equipamentos em **espaços** (slots), um item por célula. A capacidade cresce com o nível do Armazém (nv1 = 16, nv2 = 24, nv3 = 32 espaços).

Os equipamentos são comprados no **Mercado** (agora em quantidade, limitados pelos espaços do Armazém) e ainda **não têm status** — isso chega com as batalhas. Cada goblin tem a própria tela de equipar, com **9 espaços rodando o personagem**: capacete, peitoral, botas, calça, **2 anéis**, arma primária, arma secundária e colar. Tocar num espaço lista os itens do tipo guardados no armazém (equipar troca a peça e devolve a antiga).

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
  abilities.js      catálogo de habilidades (3 espaços por goblin)
  raid.js           balão, mapa das ilhas, exploração, caça e patrulhas
  creatures.js      quadros das animações de lobo e gêmeos (gerado, não editar)
  passage.js        passagem em túnel entre a ilha e a sala de batalha
  battle.js         combate por turnos (ataque normal)
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
/tmp/pv/bin/python tools/expand_wolf_frames.py   # gera os quadros de lobos/gêmeos (requer Pillow)
bash    tools/test.sh               # roda as 7 suítes de teste
```

> **Importante:** depois de mexer em `js/`, `css/` ou `assets/`, rode o
> `build_singlefile.py` — senão o arquivo jogável fica para trás.

## ✅ Testes

453 testes automatizados, sem navegador (`bash tools/test.sh`):

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

**Etapa 1.7 — Armazém & Inventário:** o **Armazém** (vila nv 2, melhorável: 16/24/32 espaços) abre o inventário da vila com todos os recursos + despensa numa área e os **itens de equipamento em slots** na outra. 13 equipamentos (sem status por enquanto): conjunto Avaritia (peitoral 120, capacete 150, calça 90 ouro), conjunto de ferro (capacete 45, peitoral 60, calça 40), botas de couro, anel de cobre/rubi, colar de presas, espada, clava e escudo. A interface de equipar tem **9 espaços rodando o goblin** (capacete, peitoral, botas, calça, 2 anéis, arma primária, arma secundária e colar) + aba **Alimentos** (alimentar goblins) + aba **Habilidades** (2 espaços por goblin, por especialidade + genéricas). Cada goblin veste o que quiser — as peças Avaritia e o peitoral de ferro mudam o sprite individualmente.

**Combate (início da Fase 3):** no canto da ilha há um **balão de ar quente abandonado**. Consertado, o botão 🎈 abre o mapa do arquipélago (ilhas em linha no mar, arraste para o lado). Em cada ilha inimiga o grupo de até **4 goblins** anda em formação; patrulhas de 4 alertam a 6 blocos (`!`) e se confundem (`?`) ao perder o rastro. Estruturas no centro dão **ouro + gemas goblinéias**; o Chefe corre atrás se você tentar destruí-las. Encostar num grupo ou no Chefe abre uma **batalha por turnos** (por enquanto só ataque normal — 3 espaços de habilidade já existem, mas entram depois).

**A seguir:** habilidades na batalha, status nos equipamentos, Ferraria/Altar/Bazar. Roadmap completo em [`docs/planejamento-jogo-gnomos.md`](docs/planejamento-jogo-gnomos.md).

### Ilha das Presas — tocas e Gêmeos da Guerra

- Expedição: até 8 goblins; escolha até 4 antes de cada encontro. No mapa,
  somente o primeiro goblin vivo representa o grupo. Os quatro escolhidos
  permanecem nas três ondas, sem cura automática entre elas.
- Madeira/pedra: 30/24 ciclos, como na vila. Cada goblin vivo soma sua taxa de
  trabalho, usando o mesmo bônus de força/velocidade da ilha normal.
- Presas: sem patrulhas ou vila central. Seis pequenas tocas têm 1/2/2 lobos;
  a toca central tem 4/4/2 (os dois últimos são os Gêmeos da Guerra).
- Mandíbula aplica sangramento por três ações de ataque: cada ação concluída
  tira 10% da vida máxima (arredondado para cima), mesmo se errar. O combo das
  manoplas conta uma vez. Um turno perdido por atordoamento não causa esse dano.
  Patas continua atordoando por um turno. Acerto normal agora fica entre 88–99%.
- As ondas preservam a vida do grupo. Os goblins marcham com o cenário
  rolando e os ataques se aproximam do alvo antes do impacto.
- Artes: `bg_den`, `bg_den_twins`, `prop_den_lair`, `twin_jaw_*`, `twin_paw_*`.
  `tools/rework_creatures.py` redesenha os 62 quadros de cada lobo com a mesma
  estrutura, paleta e pontos de armadura. Corrida dos animais tem oito quadros.
- Prévia direta de combate: `?demo=battle`; chefes: `?demo=twins`.

### Baús de toca e padrão de equipamentos

Baús não são mais espalhados pelas ilhas. A última baixa da última onda faz
surgir um baú: madeira desgastada nas tocas, ossos e tranca de caveira na toca
central. Tocar no baú revela a fila de recompensas numa faixa azul; tocar fora
dele pula a apresentação. Após revelar, qualquer toque sai da toca. Os recursos
são concedidos exatamente uma vez, inclusive ao pular.

As Manoplas do Lobo são exclusivas do baú central e ocupam as duas mãos com
uma única unidade. Substituir qualquer mão remove o par inteiro. O ataque faz
dois testes de acerto; apenas dois acertos atordoam o alvo vivo por um turno.

Padrão obrigatório para novos itens:
- Arte de chão separada, flutuação e brilho azul; ícone de inventário separado.
- Só peitoral, capacete, calças e as duas mãos alteram a skin. Acessórios não.
- Peças visíveis usam camadas opacas alinhadas quadro a quadro em todas as
  animações. Roupas permanecem no cadáver; armas saem da skin e caem no chão.
- Armas caídas são recolhidas ao armazém ao encerrar/sair do combate, sem duplicar
  itens de duas mãos. Não são reequipadas automaticamente.
- `tools/rework_equipment.py` gera os novos ícones, versões de chão e overlays
  opacos não-Avaritia. Os arquivos de Avaritia são preservados. `?demo=chest` e `?demo=chest_loot` mostram a cena de recompensa.

### Conclusão, repetição e caça

- O mapa marca `✓ OK` somente após derrotar todas as tocas (incluindo a central)
  **e sair da ilha**. A ilha permanece acessível. Como o salvamento continua
  desativado durante desenvolvimento, a marca dura a sessão atual.
- Nas revisitas de uma ilha concluída, batalhas/baús só rendem ouro e runas
  goblins; não repetem equipamentos especiais, materiais de baú ou XP. Coleta
  de árvores, pedras e caça permanecem disponíveis.
- Árvores têm 30 unidades; pedras, 24. A velocidade de trabalho continua a mesma.
- Animais têm vida (javali 18, cervo 12, lebre 8), fogem ao detectar o líder a
  110 pixels e correm a 30 px/s contra pelo menos 72 px/s do grupo. Caça dá
  `meat` (carne), separado de `food` da fazenda. Carne fica no armazém, ainda
  sem receita própria. Nenhuma caça alerta patrulhas. Colmeias foram removidas.
- Cavernas: parede só no topo, campo de batalha no chão e personagens maiores,
  mais próximos e com sombra. Não há mais HUD da vila sobre a cena de batalha.

### Correções de expedição e animação (12/10/2026)

- Lobos usam novamente a arte original preservada em `art-source/wolves-original`
  (origem: `72e94b2`), sem o redesenho procedural. Ataques foram ordenados,
  o fundo branco externo da mandíbula foi removido e as mortes usam a queda
  original com patas dobradas e pose final estável. O combate aguarda a queda
  antes de trocar de onda ou abrir a recompensa.
- Animais mantêm a arte original, com patas articuladas individualmente em oito
  quadros. A fuga busca trechos caminháveis e tem margem para não inverter a
  direção a cada instante. Não há mais balanço vertical do sprite inteiro.
- Madeira/pedra/carne aparecem em cartões com ícone. Cada árvore e pedra conta
  o total já extraído daquela fonte, inclusive ao interromper e retomar a coleta.
- Tocas e toca central derrotadas ficam guardadas por ilha entre expedições
  parciais, bloqueando novas lutas e manoplas duplicadas. Ao concluir tudo e
  confirmar a saída, a ilha recebe OK; revisitas completas continuam limitadas
  às recompensas de repetição. Como o salvamento está desativado durante o
  desenvolvimento, esse progresso vale durante a sessão, não após recarregar.
- Botão de saída e retorno ao balão pedem confirmação Sim/Não, pausando a
  expedição. Não fecha o aviso e permite continuar sem reabri-lo automaticamente.

### Animações fluidas, caça e passagem (13/10/2026)

- Lobos e Gêmeos da Guerra têm mais quadros: lobo com 10 em repouso, 16 andando,
  21 atacando, 33 em dano e 13 na queda; Mandíbula e Patas têm 10/16/17/5/13 e
  8/16/17/5/13. Os quadros novos são intermediários entre as poses da arte-fonte
  (união de silhueta, sem ruído de dither), com os pés ancorados na linha do
  repouso. Isso corrige a "decolagem" da Mandíbula no ataque. A duração total de
  cada animação foi mantida, então a velocidade geral não muda.
- A arte-fonte desses quadros é `art-source/wolves-base/` (cópia dos quadros
  anteriores). `tools/expand_wolf_frames.py` gera `assets/sprites/raid/wolf_*`,
  `twin_jaw_*` e `twin_paw_*`, atualiza o manifest e recria `js/creatures.js`.
  Não há mais dependência de `rework_creatures.py` para lobos: rodar esse script
  sobrescreve os quadros expandidos e não deve ser usado para eles.
- Ataque do lobo mapeia a animação linearmente sobre a janela de contato, então
  o movimento não trava perto do alvo. Goblins mantêm o ritmo anterior.
- Caça: o grupo passa a perseguir só acima de 30 px do animal e golpeia até 30 px,
  com histerese para não alternar ataque↔andar a cada quadro. A fuga escolhe
  trechos caminháveis de 64/40 px e, encurralado, tenta 16 direções de 28 px.
  Ao fugir, o animal anda (não fica parado) e se redireciona após 0,2 s parado.
  Grupos que tocam uma toca ou covil disparam a batalha como antes; isso não é
  travamento de caça.
- Passagem: ao entrar numa toca ou covil, o grupo caminha por um túnel
  (`bg_den_passage.png`, ~3,4 s, com zoom em direção ao fundo) antes da sala de
  batalha. Os pés dos goblins são calculados no espaço da arte e passam pelo
  mesmo zoom do fundo, então ficam sobre o chão e nunca na parede (coberto por
  testes). Toque pula a passagem após 0,6 s. Combates fora de tocas e covil seguem direto.
- Os pés de todos os quadros de lobo ficam na mesma linha do repouso, então o
  lobo não flutua nem "decola" durante o ataque ou a queda.

- Ajustes da prévia: o dano dos gêmeos (5 quadros) não dura mais que 0,5 s, o que
  eliminava a sensação de câmera lenta. Pontos claros soltos da arte de ataque
  foram removidos na geração. Entre ondas, a passagem em túnel aparece antes da
  próxima onda (a batalha espera a passagem terminar). Modo instantâneo (testes)
  continua sem passagem.
- Limitações conhecidas: o brilho cinza em volta da cabeça da Mandíbula (quadro de
  ataque 9) é parte da arte-fonte e continua visível. O ataque da Mandíbula é
  desenhado menor na arte-fonte (pose agachada); corrigir exige redesenho ou escala
  uniforme, ainda não feito.

### Animais e inimigos na exploração (14/10/2026)

- Lobos na exploração usavam os contadores de quadros dos animais: andavam só com
  os 8 primeiros de 16 quadros e ficavam parados com 5 de 10. Agora usam
  `creatures.js` (16 andando, 10 repouso, 13 morte), com a mesma duração de ciclo.
- Animal abatido usa a arte de morte (`animal_<tipo>_death`, deitado de lado),
  desce do ar em 0,45 s e some em fade nos últimos 0,35 s. Antes era o sprite de
  repouso girado no lugar, afundando no chão.
- Animal atingido usa a arte de dano (`animal_<tipo>_hurt`) por 0,18 s, com um leve
  tremor e clareamento.
- Sprites de javali, veado e lebre mantêm a proporção da arte original (antes
  esticavam ~10%) e são suavizados ao reduzir (menos chiado nas patas).
- Chefe da ilha já animava (repouso e investida); conferido, sem alteração.
- Arte nova dos animais (javali, veado e lebre), gerada a partir do sprite de
  repouso com o mesmo estilo, fundo magenta removido, mesma caixa e linha dos pés.
  Está em `assets/sprites/raid/animal_<tipo>_{hurt,death}.png`. A suíte de render
  confere que todo animal tem repouso, caminhada, dano e morte no manifest.
- Mandíbula de metal (lobo gêmeo, ataque): brilho picotado removido e corpo levado à
  escala do repouso (×1,3, pés ancorados); fragmentos soltos são descartados. Gerada
  por `tools/expand_wolf_frames.py`.
- Javali com 16 quadros de caminhada (`ANIMAL_WALK_FRAMES` em `js/raid.js`): os 8
  originais em posições pares e 8 intermediários gerados em posições ímpares, mesmo
  ciclo de 0,8 s. Veado e lebre continuam com 8 quadros.
- Caminhada do veado refeita sem IA por `tools/make_deer_walk.py`: só as pernas se
  movem (2 px no casco, fases opostas) a partir do repouso. Os quadros antigos tinham
  linhas em V sob a barriga e pixels soltos nas patas.
- Mandíbula de aço continua com o brilho cinza e o ataque menor da arte-fonte;
  ainda não foi redesenhada.

`python3 tools/rework_creatures.py` reproduz as correções a partir das imagens
originais preservadas (equipamento e armadura Avaritia não são afetados); para lobos use `expand_wolf_frames.py`, como descrito acima.
