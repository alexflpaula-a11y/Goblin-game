# Itens — design padrão

Todo item do jogo é criado numa pasta própria: `sprites/itens/<id_do_item>/`

```
sprites/itens/peitoral_ferro/     ← 1º item (referência do padrão)
  icon.png                        ← 16×16  — versão de inventário
  drop.png                        ← 32×32  — versão caída no chão (brilho azul embutido)
  goblin_idle_0..4.png            ← 32×32  — goblin EQUIPADO (todas as animações)
  goblin_walk_0..7.png
  goblin_attack_0..16.png
  goblin_hurt_0..16.png
  goblin_death_0..14.png          ← inclusive a pose caída no chão
  item.json                       ← metadados (nome, slot, raridade, bônus)

sprites/itens/capacete_avaritia/  ← conjunto Avaritia (ref.: “Avaritia armour.zip”)
sprites/itens/peitoral_avaritia/     peças SEPARADAS — 3 formas + item.json cada
sprites/itens/calca_avaritia/
sprites/itens/combo_capacete_peitoral/  ← pares (2 peças juntas)
sprites/itens/combo_capacete_calca/
sprites/itens/combo_peitoral_calca/
sprites/itens/conjunto_avaritia/     ← COMPLETO: tudo preto, só orelhas de fora
```

## As 3 formas (obrigatórias em todo item)

1. **Caído no chão** — `drop.png` 32×32 com brilho azul embutido. No jogo, o item
   **flutua** (sobe e desce suavemente) e o **brilho azul pulsa**.
2. **No inventário** — `icon.png` 16×16, encaixado no slot.
3. **Equipado no goblin** — moldado pixel a pixel sobre os sprites 32×32:
   pinta **somente os pixels do corpo** (nunca rosto, braços, cinto ou pés),
   é **100% opaco** (não transparece) e acompanha **todas** as animações,
   inclusive a pose caída no chão (morte).

## Quem ganha a 3ª forma (skin no sprite)

- **Peitoral, capacete, calças**
- **Mão primária**: espada, arco, cajado, orbe de cura, machado, picareta, …
- **Mão secundária**: escudo, livro de magia, bolsa de flechas, medkit, lanterna, …

**Não ganham skin** (aparecem só no inventário): botas, amuletos, anéis, colares etc.

## Regra de morte

- **Armas caem no chão quando o goblin morre** (viram o `drop.png` no mapa).
- Armaduras e os demais equipamentos **continuam no corpo** durante a queda.

## Guarda de rosto (regra dura — vale para TODO equipamento)

Nenhum equipamento pode **jamais** pintar sobre o rosto do goblin. O gerador
verifica frame a frame e **erro se violar** (nada é gerado):

- frames de pé (olhos visíveis): pixel pintado precisa estar a **≥ 4 px dos olhos**;
- frames deitado/virado (só a boca visível): pixel pintado precisa estar
  **abaixo da linha da boca** e a **≥ 2 px da boca**.

Além disso, só pode pintar **pixel verde e opaco do corpo** — nunca rosto,
braços, cinto, pés ou áreas transparentes.

## Como gerar

Os sprites são gerados por script a partir dos frames originais do goblin
(extraídos do `vila-de-goblins-jogavel.html`):

```bash
python3 sprites/itens/gerar_item.py      # gera TODOS os itens (ferro + avaritia)
python3 sprites/itens/gerar_conjunto.py  # compõe o conjunto avaritia (3 peças juntas)
```

Para criar um item novo: acrescente um bloco em `ITENS` no `gerar_item.py`
(id, zona, estilo, ícone 16×16 e, se for peça de skin, as máscaras dos
frames deitados). As **zonas** disponíveis:

- `torso` — banda olhos+4..olhos+8 (em pé) / máscaras abaixo da boca (deitado)
- `cabeca` — coroa (topo da cabeça, ≥2px acima dos olhos) / alto da cabeça (deitado)
- `pernas` — tanga marrom + pernas verdes abaixo do torso

Os previews de referência estão na raiz do repo:
`preview-item-peitoral-ferro.html` e `preview-conjunto-avaritia.html`.
