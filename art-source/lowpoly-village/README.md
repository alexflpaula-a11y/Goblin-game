# Estruturas e cenário em low-poly (IA)

Substituição da pixel art de **estruturas e cenários** por renders low-poly
gerados por IA, no mesmo estilo do low-poly que já existe no jogo.

Regra deste trabalho: **nada entra no jogo sem aprovação explícita**. O lote é
gerado em `candidates/` (staging), conferido numa folha de aprovação e só
depois publicado em `assets/sprites/`.

---

## 1. O low-poly que já existe no jogo (referência de estilo)

| Conjunto | Arquivos no jogo | Tamanho | Origem |
|---|---|---|---|
| Javali, veado e lebre | `assets/sprites/raid/animal_*` (57 quadros) | 112×82, 83×96, 79×72 | IA low-poly |
| Lobo | `assets/sprites/raid/wolf_*` (56 quadros) | 48×32 | IA low-poly |
| Gêmeos da Guerra (Mandíbula) | `twin_jaw_*` (40 quadros) | 56×36 | IA low-poly |
| Gêmeos da Guerra (Patas) | `twin_paw_*` (39 quadros) | 56×36 | IA low-poly |

**192 quadros** no total. Fonte dos gêmeos em `art-source/gemeos-lowpoly/`;
`art-source/wolves-original/` e `wolves-base/` guardam os quadros preservados do
lobo e dos gêmeos. `art-source/animals-original/` é a versão **em pixel art**
dos animais, que não é a usada hoje no jogo.

Características que definem o estilo (checklist dos prompts):

- render 3D **low-poly** com facetas/triângulos chapados e visíveis;
- **sem contorno preto**, sem textura pintada e sem gradiente suave;
- animais e lobos em vista 3/4; **estruturas em vista frontal 2D (elevação
  ortográfica)**, como a pixel art antiga, sem perspectiva isométrica;
- objeto apoiado na base, luz ambiente suave vinda de cima/esquerda;
- cores naturais e saturadas, sombra própria apenas (sem sombra projetada no chão);
- fundo **magenta chapado `#FF00FF`**, sem texto, sem moldura, sem cenário;
- silhueta legível no tamanho nativo do jogo (um plano dominante, poucas faces).

## 2. O que ainda é pixel art (alvo deste trabalho)

**39 assets**: 15 prédios, 2 divindades, 4 nós de recurso, 3 estruturas de
raid, 4 baús, 3 balões, 5 ilhas e 3 cenários de fundo. Todos já existem no
`assets/manifest.json`; a integração troca o conteúdo do mesmo caminho, sem
mexer em código de desenho nem em nomes lógicos.

Ficam **fora** deste pedido (não são estrutura/cenário): goblins, variações,
armaduras e overlays, ícones de UI, ícones de recurso, comidas, itens e o
projétil `fx_pedra_divina`.

## 3. Tamanhos nativos (1:1 no jogo)

O canvas usa `imageSmoothingEnabled = false` na maioria dos desenhos, então o
sprite é produzido no tamanho em que o jogo o desenha.

| Tipo | Tamanho | Quem desenha |
|---|---|---|
| Prédios | 64×64 | `village.js` (`s.x-32, s.y-60, 64, 64`) |
| Divindades | 64×64 (teste exige exato) | `village.js` 64×64; `deities.js` amplia para 72×72 |
| Árvore / pedra | 48×48 | `nodes.js` e `raid.js` (`size = 48`) |
| Toco / entulho | 24×24 | `nodes.js` (`size = 24`) |
| Toca | 52×34 | `raid.js` |
| Toca central (covil) | 160×87 | `raid.js` |
| Colmeia | 32×40 | `raid.js` |
| Baú | 24×24 | `raid.js` |
| Baú de recompensa | 160×140 | `treasure.js` |
| Balão (pronto / voando / destruído) | 42×54 / 46×58 / 56×38 | `raid.js` |
| Ilhas | 156×108 | `raid.js` |
| Mapa-múndi do mar | 640×360 | `raid.js` |
| Fundos de caverna / passagem | 640×360 | `raid.js`, `passage.js` |

Os fundos de caverna são opacos: não passam pelo chroma key nem pelo recorte
de alpha; entram direto em 640×360.

## 4. Pipeline

`tools/lowpoly_sprites.py`

1. `raw/` — render da IA com fundo magenta `#FF00FF` chapado;
2. chroma key pela distância à cor da borda + despill do roxo (sem franja);
3. corte no conteúdo real;
4. redução LANCZOS em alpha pré-multiplicado (sem halo);
5. acabamento: unsharp suave, saturação +12%, contraste +5% e paleta de
   40 cores — em 64 px as facetas do render ficam macias, e isso devolve a
   quina e o plano chapado do resto do jogo;
6. saída em `candidates/` (**staging**, não é lido pelo jogo).

`tools/aprovacao.py LOTE ids...` monta a folha de aprovação com os originais,
o antes/depois em tamanho nativo (com goblin para escala) e uma cena.

`python3 tools/lowpoly_sprites.py --publish` copia **somente** os candidatos
aprovados para `assets/sprites/`. Depois a integração ainda exige:

```bash
python3 tools/build_singlefile.py   # reconstrói vila-de-goblins-jogavel.html
bash tools/test.sh                  # 7 suítes
```

## 5. Lotes (10 renders por lote, no máximo)

| Lote | Conteúdo | Qtde | Status |
|---|---|---|---|
| **01** | `house`, `ferraria`, `node_tree`, `node_rock` | 4 | **árvore/pedra aprovadas; casa/ferraria refeitas em 2D, aguardando aprovação** |
| **02** | `altar`, `armazem`, `bar`, `cozinha`, `estabulo`, `fazenda`, `mercado`, `porto`, `quartel`, `questboard` | 10 | **aguardando aprovação** |
| 03 | `serraria`, `construction_1`, `construction_site`, `grande_arvore`, `golem_pedra`, `node_tree_stump`, `node_rock_rubble`, `prop_den`, `prop_hive`, `chest_closed` | 10 | não gerado |
| 04 | `chest_open`, `reward_chest_wood`, `reward_chest_bone`, `balloon_ready`, `balloon_flying`, `balloon_wrecked`, `island_home`, `island_fangs`, `island_smoke`, `island_iron` | 10 | não gerado |
| 05 | `prop_den_lair`, `islands_sea`, `bg_den`, `bg_den_twins`, `bg_den_passage` | 5 | não gerado |

Destino de cada asset:

| Lote | id do candidato | arquivo no jogo |
|---|---|---|
| 01 | `house` | `buildings/building_house_1.png` |
| 01 | `ferraria` | `buildings/building_ferraria_1.png` |
| 01 | `node_tree` | `nodes/node_tree_0.png` |
| 01 | `node_rock` | `nodes/node_rock_0.png` |
| 02 | `altar` | `buildings/building_altar_1.png` |
| 02 | `armazem` | `buildings/building_armazem_1.png` |
| 02 | `bar` | `buildings/building_bazar_1.png` (o id interno `bazar` continua; só a arte virou bar) |
| 02 | `cozinha` | `buildings/building_cozinha_1.png` |
| 02 | `estabulo` | `buildings/building_estabulo_1.png` |
| 02 | `fazenda` | `buildings/building_fazenda_1.png` |
| 02 | `mercado` | `buildings/building_mercado_1.png` |
| 02 | `porto` | `buildings/building_porto_1.png` |
| 02 | `quartel` | `buildings/building_quartel_1.png` |
| 02 | `questboard` | `buildings/building_questboard_1.png` |
| 03 | `serraria` | `buildings/building_serraria_1.png` |
| 03 | `construction_1` | `buildings/building_construction_1.png` |
| 03 | `construction_site` | `buildings/building_construction_site.png` |
| 03 | `grande_arvore` | `deities/building_grande_arvore_1.png` |
| 03 | `golem_pedra` | `deities/building_golem_pedra_1.png` |
| 03 | `node_tree_stump` | `nodes/node_tree_stump.png` |
| 03 | `node_rock_rubble` | `nodes/node_rock_rubble.png` |
| 03 | `prop_den` | `raid/prop_den.png` |
| 03 | `prop_hive` | `raid/prop_hive.png` |
| 03 | `chest_closed` | `raid/chest_closed.png` |
| 04 | `chest_open` | `raid/chest_open.png` |
| 04 | `reward_chest_wood` | `raid/reward_chest_wood.png` |
| 04 | `reward_chest_bone` | `raid/reward_chest_bone.png` |
| 04 | `balloon_ready` | `raid/balloon_ready.png` |
| 04 | `balloon_flying` | `raid/balloon_flying.png` |
| 04 | `balloon_wrecked` | `raid/balloon_wrecked.png` |
| 04 | `island_home` | `ui/island_home.png` |
| 04 | `island_fangs` | `ui/island_fangs.png` |
| 04 | `island_smoke` | `ui/island_smoke.png` |
| 04 | `island_iron` | `ui/island_iron.png` |
| 05 | `prop_den_lair` | `raid/prop_den_lair.png` |
| 05 | `islands_sea` | `ui/islands_sea.png` |
| 05 | `bg_den` | `raid/bg_den.png` |
| 05 | `bg_den_twins` | `raid/bg_den_twins.png` |
| 05 | `bg_den_passage` | `raid/bg_den_passage.png` |

## 6. Status do lote 01

| id | destino no jogo | status |
|---|---|---|
| `node_tree` | `nodes/node_tree_0.png` | aprovada |
| `node_rock` | `nodes/node_rock_0.png` | aprovada |
| `house` | `buildings/building_house_1.png` | refeita em 2D, aguardando aprovação |
| `ferraria` | `buildings/building_ferraria_1.png` | refeita em 2D, aguardando aprovação |

As primeiras versões da casa e da ferraria eram 3/4 isométricas; foram
reprovadas e movidas para `rejected/` (`house_3d.png`, `ferraria_3d.png`,
`ferraria_front_wide.png`). A direção aprovada para estruturas é **frente reta
2D**, não isométrica.

Folha de aprovação: `preview/aprovacao-01.png`.

## 7. Lote 02 — decisões de arte

- O antigo **bazar (barraca de feira)** foi **substituído por um bar/taverna**,
  a pedido. O arquivo de destino continua `buildings/building_bazar_1.png` e o
  id interno do prédio continua `bazar`; **nenhuma mecânica foi alterada**.
- **Armazém, cozinha e bar** foram refeitos para não se parecerem entre si:
  - `armazem`: celeiro alto e estreito, base de pedra, sótão de madeira, sarilho
    no topo e portas verticais grandes — sem toldo, sem chaminé, sem caldeirão;
  - `cozinha`: cozinha aberta de quintal, quatro postes e telhado de palha, forno
    de barro em cúpula, caldeirão no tripé e bancada com legumes — sem parede
    frontal e sem fachada de pedra;
  - `bar`: taverna enxaimel, placa pendurada, janelas quentes, barris e banco.
- **Fazenda** refeita em frente reta (antes tinha um leve 3/4).

Folha de aprovação do lote: `preview/aprovacao-02.png`.
Ferramenta: `tools/aprovacao_lote.py LOTE ids...`.

## 8. Unificação de estilo (paleta comum)

Cada render da IA escolhe sozinho saturação e temperatura, e o lote 02 ficava
com peças "de jogos diferentes" (fazenda verde-limão contra o restante terroso).
`tools/lowpoly_harmonize.py` resolve isso sem descaracterizar nenhuma peça:

1. junta os sprites **já aprovados** (casa, ferraria, árvore, pedra) com o lote;
2. quantiza o conjunto em uma paleta única (`--palette 64`);
3. remapeia cada pixel do lote para a cor mais próxima dessa paleta,
   preservando o alpha.

Toda peça publicada passa por esse passo depois de `lowpoly_sprites.py`.

## 9. Auditoria de encaixe (linha de base)

`tools/auditoria_encaixe.py` compara, sprite por sprite, o recorte **antigo**
(revisão `e565e0b`) com o **novo**:

- **folga inferior** — quantos pixels vazios existem abaixo do conteúdo. A
  pixel art antiga deixava **1 px** nos prédios; se o novo deixasse 0, a
  estrutura afundava 1 px em relação às vizinhas. O pipeline agora tem
  `'gap': 1` em todo prédio;
- **centro horizontal** — deslocamento máximo aceito: 1,5 px;
- **largura/altura** — não pode estourar a caixa nem ficar abaixo de 70% dela
  (estruturas baixas por natureza, como o balcão do mercado, são respeitadas);
- **bordas** — nenhum pixel opaco pode encostar na borda da caixa (corte);
- **franja magenta** — pixels arroxeados com alpha > 40 devem ser 0.

`tools/validar_encaixe.py` gera a folha visual `preview/validacao-encaixe.png`
com a linha do chão marcada, e `tools/cena_vila.py` monta
`preview/cena-vila.png` com os sprites reais em 1:1 sobre a cor da grama.

Correções desta rodada: `'gap': 1` nos 12 prédios, despill extra de magenta
(a ferraria tinha 12 px de franja roxa) e refeitos `altar`, `estabulo` e
`quartel`, que tinham vindo largos demais e ficavam menores que a arte antiga.

## 10. Animações (em andamento)

Quadros-chave gerados por IA e processados pelo mesmo pipeline, com tamanho
nativo do desenho no jogo. Os quadros **intermediários não são gerados** por IA:
são derivados por interpolação, como já é feito nos lobos e gêmeos
(`tools/expand_wolf_frames.py`), para a animação não "tremer" entre quadros.

| Animação | Quadros-chave | Tamanho | Estado |
|---|---|---|---|
| Baú abrindo | `chest_closed`, `chest_open_1`, `chest_open_2` | 24×24 | gerado |
| Árvore cantando | `deity_tree_sing_0..2` (boca fechada → aberta) | 64×64 | gerado |
| Notas musicais | `fx_notas` | 24×24 | gerado |
| Árvore nascendo do chão | muda → árvore grande | 64×64 | pendente |
| Golem: forja e arremesso | juntar mãos → pedra → ombro → giro de quadril → arremesso | 64×64 | pendente |
| Pedra quicando e deslizando | arco → 1º quique → deslize →parada | 32×32 | pendente |

Publicado nesta rodada: baú (2 quadros novos), árvore cantando (3 quadros) e
notas. As três animações restantes dependem de aprovação e continuam no próximo
turno, respeitando o limite de 10 imagens por turno.
