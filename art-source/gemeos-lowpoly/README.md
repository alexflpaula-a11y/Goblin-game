# Gêmeos em estilo low-poly (fonte e integração)

Originais gerados por IA em 1200×880. Os sprites usados pelo jogo estão em `assets/sprites/raid/` (56×36), gerados a partir destes PNGs.

## Pipeline
1. **Cor:** cada quadro recebe ganho por canal para igualar o corpo à base (Mandíbula G≈95, Patas G≈103). Vermelho e amarelo dos efeitos ficam intactos.
2. **Escala única por criatura:** `tools/cut_gemeos_set.py` mede a extensão real do lobo em todos os quadros de uma criatura (ignora ruído isolado) e usa uma só escala. Os pés ficam na última linha (y=35) e o corpo é centralizado. Resultado: Mandíbula 0,056; Patas 0,057. Quadros do mesmo lobo não mudam de tamanho na animação.
3. **Corte:** máscara por distância à cor de fundo (55,27,8), maior bloco conectado, 56×36.

## Padrões
- **Mandíbula:** placa de aço única do queixo à bochecha, com dentes, visível com a boca fechada. Sem pelo sobre a placa. Pernas laranja normais (sem aço).
- **Patas:** duas pernas de aço com garras. Sem placa de mandíbula. Corpo laranja igual ao lobo normal.

## Estado dos conjuntos (integrados)
| Conjunto | Mandíbula | Patas |
|---|---|---|
| Repouso | `mandibula_v2_idle_0..4` (5) | `patas_idle_0,2,3,4` (4) |
| Caminhada | `mandibula_v2_walk_key_N` e `mid_N` (16) | `patas_walk_key_N` e `mid_N` (16) |
| Dano | `mandibula_v2_hurt_0..2` (3) | `patas_hurt_0..2` (3) |
| Ataque | `mandibula_fx_atk_0..8` (9), corte vermelho nos quadros 3 a 5 | `patas_fx_slap_0..8` (9), impacto nos quadros 3 e 4 |
| Morte | `mandibula_v2_death_0..6` (7) | `patas_death_0..6` (7) |

Ordem na caminhada do jogo: `walk_2N = key_N`, `walk_2N+1 = mid_N` (mid_N fica entre key_N e key_N+1).

Contagens batem com `js/creatures.js`: twin_jaw idle 5, walk 16, attack 9, hurt 3, death 7; twin_paw idle 4, walk 16, attack 9, hurt 3, death 7.

## Correções desta rodada
- `patas_death_2`: refeito. A pata esticada saiu. Pose deitada com as duas patas de aço.
- `mandibula_v2_death_2`: refeito. Sombra de chão removida.
- `mandibula_v2_walk_mid_3`: linha de chão laranja atravessando a imagem removida (edição do próprio quadro).
- Cor: morte das Patas e Mandíbula e caminhada igualadas à base, com ganho limitado a 0,9–1,15.
- Escala: antes cada quadro era ajustado ao próprio contorno, o que fazia o lobo mudar de tamanho na animação (ex.: `twin_jaw_walk_7`). Agora a escala é única.
- `TWIN_JAW_BITE_PX` zerado em `js/battle.js` (o avanço da mordida está nos quadros).

## Verificação
- Inspeção visual de todos os 79 quadros de jogo em folha ampliada: sem sombra de chão, sem linha de chão, sem pata esticada, placa de aço da Mandíbula em todos, duas pernas de aço nas Patas.
- Sem pedra na boca em nenhum quadro atual. A pedra reportada antes (`atk_3` antigo) foi reprovada e não está nos quadros integrados. Se você tiver outro local onde a viu, me diga para conferir.
- Aço escuro das pernas das Patas é fino e escuro. A medição por cor não o detecta, então a conferência foi visual.
- Testes do jogo: todas as suítes passam. Arquivo único reconstruído.

## Limitações conhecidas
- Em 56×36 o estilo low-poly contrastava com a pixel art do restante do jogo.
  Cenários e estruturas foram facetados em 20/10/2026; o que falta está em
  `docs/lowpoly.md`. Todos os animais (inclusive lobo comum e presas) já
  nascem low-poly na arte-fonte — esta pasta cobre só a pipeline por IA
  dos dois chefes.
- Pernas de aço das Patas ficam finas e escuras em alguns quadros de caminhada.

## Histórico
- Originais no Git: 82 PNGs de 1200×880 (~80 MB), decisão de guardar os originais aceita pelo usuário.
- Descartados: versões cinzas das Patas, caminhada de 8 quadros-chave das Patas, Mandíbula v1, quadros reprovados (`atk_3` antigo com pedra, `atk_4` antigo com duas cabeças, `mand_atk_v3_5`, `patas_slap_4`, `patas_slap_6`, `patas_death_2` v14/v15).
