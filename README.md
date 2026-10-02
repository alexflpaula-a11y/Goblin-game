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
  goblins/          os 45 GIFs de variação da arte antiga (histórico)
  goblins-v2/       folhas de conferência do goblin atual (base, variações, equipamentos)
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
python3 tools/gen_goblin_v2.py             # goblin base + as 45 variações (2852 quadros)
python3 tools/gen_gear_v2.py               # armaduras e armas encaixadas no goblin
python3 tools/gen_goblin_variations.py     # (legado) extraía as variações dos GIFs antigos
python3 tools/unbuild.py            # extrai a fonte de volta a partir do build
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

PNGs **32×32** referenciados por **nome lógico** no `manifest.json`. Se um PNG não existir, um placeholder é desenhado automaticamente (o jogo nunca quebra). Os goblins têm **45 variações físicas** — dente dourado, tapa-olho, cicatrizes, albinismo, tatuagens e combinações — cada uma com os 62 quadros de `idle/walk/attack/hurt/death`.

Desde a arte atual, nada disso é desenhado quadro a quadro: existe um **rig**. O goblin base **não é um desenho novo** — ele é recortado, pixel a pixel, da arte de referência em `art-source/goblins-v2/referencia.jpg` (64×64). O pipeline reduz a arte para a escala do jogo (26 px de altura num canvas 32×32), limpa a compressão JPEG numa paleta de 12 cores e **fatia o resultado em partes** (cabeça com as duas orelhas, tronco com o avental de couro, braço esquerdo, braço direito com a adaga, perna esquerda, perna direita, lâmina). Cada parte já carrega o contorno e o sombreado originais; o rig só reposiciona as peças por quadro e, por cima, pinta o rosto, a variação e a armadura. Por isso um ajuste no recorte se propaga para os 2852 quadros de uma vez.

Comparação lado a lado em `art-source/goblins-v2/base-zoom.png`; a arte limpa em 64×64 fica em `referencia-limpa.png`.

| arquivo | papel |
| --- | --- |
| `tools/goblin_rig.py` | partes recortadas da referência, paleta, pontos de ancoragem, PNG indexado |
| `tools/goblin_anim.py` | as 62 poses das 5 animações |
| `tools/goblin_variations.py` | as 45 aparências como receitas de traços (cicatriz, atadura, albinismo…) |
| `tools/goblin_gear.py` | armaduras e armas, ancoradas às partes do corpo |
| `tools/gen_goblin_v2.py` / `tools/gen_gear_v2.py` | geram os PNGs |

Cada traço de variação é aplicado em coordenadas **relativas à cabeça/braço daquele quadro**, então a marca acompanha o goblin em qualquer pose. Os overlays de armadura também não são desenhados à mão: são a **diferença** entre o quadro vestido e o mesmo quadro nu, o que torna o encaixe exato por construção. Prédios, recursos e comidas são pixel art autoral gerada por `tools/gen_sprites.py`.

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

**A seguir:** Fase 2 (Ferraria, Altar, Bazar) → Fase 3 (combate por turnos — quando os equipamentos ganham status). Roadmap completo em [`docs/planejamento-jogo-gnomos.md`](docs/planejamento-jogo-gnomos.md).
