# Gêmeos em estilo low-poly (fonte, ainda não integrada)

Originais gerados por IA, em 1200×880, comprimidos sem perda. **Não são os sprites do jogo.**
Os sprites usados pelo jogo continuam em `assets/sprites/raid/` (pixel art 56×36) até a etapa de corte e integração.
Esta pasta está em ~61 MB: é o custo de guardar os originais no Git, decidido com o usuário.

Corpo: lobo normal em laranja-acastanhado. Mandíbula e Patas são o lobo com a peça de aço.

## Inspeção (última rodada)
- Todos os quadros estão sem sombra de chão, exceto os que foram corrigidos (ver `death_3` abaixo).
- Quase todos têm 1 pixel isolado nas bordas direita/inferior. É ruído do gerador: o corte com maior componente conectado descarta esse pixel.
- `patas_atk_5`: 1 pixel de borda, mesmo caso.
- Conformidade medida em miniatura e em ampliação pontual. Não é uma conferência quadro a quadro em ampliação.

## Patas (duas patas dianteiras de aço com duas garras cada)
| Conjunto | Código (`js/creatures.js`) | Arquivos aqui | Estado |
|---|---|---|---|
| Base | — | `patas_base_laranja.png` | Aceita. Duas garras confirmadas em ampliação |
| Repouso | `idle: 4` | `patas_idle_0..4` (5) | Pendente: escolher 4. Sugestão: base, `idle_1`, `idle_2`, `idle_3`. `idle_4` fica de fora |
| Caminhada | `walk: 16` | nenhum | Pausada: pata distante fora do modelo nas tentativas anteriores |
| Dano | `hurt: 3` | `patas_hurt_0..2` | Aceito |
| Ataque | `attack: 9` | `patas_atk_0..8` | Aceito; `atk_5` com pata mais esticada, conferir no jogo |
| Morte | `death: 7` | `patas_death_0..6` | Aceito; `death_3` e `death_4` refeitos |

## Mandíbula v2 (mandíbula de aço grande e visível, também com a boca fechada; pernas sem aço)
A v1 tinha mandíbula pequena e não aparecia com a boca fechada. A v2 foi refeita a partir dela; os quadros da v1 foram removidos.

| Conjunto | Código | Arquivos aqui | Estado |
|---|---|---|---|
| Base | — | `mandibula_base_v2.png` (= `mandibula_v2_idle_0`) | Aceita |
| Repouso | `idle: 5` | `mandibula_v2_idle_0..4` (5 de 5) | Aceito |
| Caminhada | `walk: 16` | `mandibula_v2_walk_key_0..7` (8 de 16) | **Provisória.** `key_3` e `key_5` com pernas a conferir. Faltam 8 intermediários |
| Dano | `hurt: 3` | `mandibula_v2_hurt_0..2` (3 de 3) | Aceito |
| Ataque | `attack: 9` | `mandibula_v2_atk_0..8` (9 de 9) | Aceito |
| Morte | `death: 7` | `mandibula_v2_death_0..6` (7 de 7) | Aceito. `death_3` refeito sem sombra |

## Descartados (não estão aqui)
- Versões cinzas das Patas (`patas_base_cinza`, `patas_key_*`): o usuário pediu o corpo laranja.
- Caminhada de 8 quadros-chave das Patas (`patas_k*`): pata distante fora do chão.
- Mandíbula v1 (base e repouso pequenos): substituída pela v2.
- Versão v3 das Patas e os primeiros quadros de morte e ataque: perdidos no reinício do ambiente.
- Quadros reprovados da v2: `idle_2` antigo (cabeça alta), `atk_3` antigo (bloco de pedra na boca), `atk_4` antigo (duas cabeças), `atk_5` antigo (corpo longo e fino), `death_3` v5 (sombra de chão).

## Pendências para integrar
1. Patas: confirmar os 4 quadros de repouso.
2. Mandíbula: conferir `walk_key_3` e `walk_key_5`; gerar 8 intermediários da caminhada.
3. Patas: caminhada (8 keys e 8 intermediários), depois de aprovar uma base de caminhada.
4. Corte com `cutlib` para 56×36, pés na linha 36, e medições.
5. Atualizar `js/creatures.js` apenas quando as contagens baterem.
6. Build, testes e conferência no navegador.
