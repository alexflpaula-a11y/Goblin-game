# Gêmeos em estilo low-poly (fonte, ainda não integrada)

Originais gerados por IA, em 1200×880, comprimidos sem perda. **Não são os sprites do jogo.**
Os sprites usados pelo jogo continuam em `assets/sprites/raid/` (pixel art 56×36) até a etapa de corte e integração.
Esta pasta tem 58 PNGs (~64 MB): 33 da Mandíbula e 25 das Patas. Guardar os originais no Git foi decidido com o usuário, mas essa decisão ainda não está confirmada para o total.

Corpo: lobo normal em laranja-acastanhado. Mandíbula e Patas são o lobo com a peça de aço.

## Padrão da Mandíbula (placa de aço única)
Uma placa de aço escura do queixo à bochecha, com dentes, visível com a boca fechada. Sem pelo sobre a placa e sem dentes soltos. Ataques com boca aberta podem mudar a pose, mas não o desenho da placa.
Os quadros v7 foram gerados a partir da base v2 para uniformizar o desenho. Os quadros da v2 com desenho fora do padrão foram substituídos.

## Inspeção (última rodada)
- Nenhum quadro tem sombra de chão. Medido: o conteúdo mais baixo fica acima de y≈760 em todos os quadros de morte e caminhada.
- Quase todos têm 1 pixel isolado nas bordas direita/inferior. É ruído do gerador: o corte com maior componente conectado descarta esse pixel.
- `patas_atk_5`: a pata estendida termina em x≈1050 de 1200, sem corte. É a pose mais longa do conjunto; conferir no jogo.
- Conformidade da Mandíbula verificada por comparação visual em folha de contato (todos os 33 quadros). A medição por cor de aço não serve, porque a iluminação varia.
- Pernas de aço das Patas: ainda não conferidas em ampliação quadro a quadro.

## Patas (duas patas dianteiras de aço com duas garras cada)
| Conjunto | Código (`js/creatures.js`) | Arquivos aqui | Estado |
|---|---|---|---|
| Base | — | `patas_base_laranja.png` | Aceita. Duas garras confirmadas em ampliação |
| Repouso | `idle: 4` | `patas_idle_0..4` (5) | Pendente: escolher 4. Sugestão: base, `idle_1`, `idle_2`, `idle_3`. `idle_4` fica de fora |
| Caminhada | `walk: 16` | nenhum | Pausada: pata distante fora do modelo nas tentativas anteriores |
| Dano | `hurt: 3` | `patas_hurt_0..2` | Aceito |
| Ataque | `attack: 9` | `patas_atk_0..8` | Aceito; `atk_5` com pata longa, sem corte |
| Morte | `death: 7` | `patas_death_0..6` | Aceito; `death_3` e `death_4` refeitos |

## Mandíbula v2/v7 (mandíbula de aço grande e visível, também com a boca fechada; pernas sem aço)
A v1 tinha mandíbula pequena e não aparecia com a boca fechada. A v2 foi refeita a partir dela; os quadros da v1 foram removidos.

| Conjunto | Código | Arquivos aqui | Estado |
|---|---|---|---|
| Base | — | `mandibula_base_v2.png` (= `mandibula_v2_idle_0`) | Aceita |
| Repouso | `idle: 5` | `mandibula_v2_idle_0..4` (5 de 5) | Aceito |
| Caminhada | `walk: 16` | `mandibula_v2_walk_key_0..7` (8 de 16) | **Provisória.** `key_0,4,5,6` são v7; `key_1,2,3,7` são v2. Pernas de `key_3` a conferir. Faltam 8 intermediários |
| Dano | `hurt: 3` | `mandibula_v2_hurt_0..2` (3 de 3) | Aceito |
| Ataque | `attack: 9` | `mandibula_v2_atk_0..8` (9 de 9) | Aceito. `atk_3` v4, `atk_4` v7, `atk_5` v3, demais v2 |
| Morte | `death: 7` | `mandibula_v2_death_0..6` (7 de 7) | Aceito. `death_0,1,2,3,6` são v7 (`death_3` sem sombra). `death_4` v2, `death_5` v5 |

## Descartados (não estão aqui)
- Versões cinzas das Patas (`patas_base_cinza`, `patas_key_*`): o usuário pediu o corpo laranja.
- Caminhada de 8 quadros-chave das Patas (`patas_k*`): pata distante fora do chão.
- Mandíbula v1 (base e repouso pequenos): substituída pela v2.
- Versão v3 das Patas e os primeiros quadros de morte e ataque: perdidos no reinício do ambiente.
- Quadros reprovados da v2: `idle_2` antigo (cabeça alta), `atk_3` antigo (bloco de pedra na boca), `atk_4` antigo (duas cabeças), `atk_5` antigo (corpo longo e fino).
- Mandíbula v4/v5 usadas antes: `atk_4` v5 e `death_3` v5 (sombra de chão), `death_3` v6 (substituído pela v7), `death_6` v4 e `atk_3` v4 (aceitos, ainda usados).

## Pendências para integrar
1. Patas: confirmar os 4 quadros de repouso.
2. Mandíbula: conferir as pernas de `walk_key_3`; gerar 8 intermediários da caminhada.
3. Patas: pernas de aço em ampliação quadro a quadro; caminhada (8 keys e 8 intermediários), depois de aprovar uma base de caminhada.
4. Corte com `cutlib` para 56×36, pés na linha 36, e medições.
5. Atualizar `js/creatures.js` apenas quando as contagens baterem.
6. Build, testes e conferência no navegador.
7. Decidir com o usuário se os ~64 MB de PNG ficam no Git.
