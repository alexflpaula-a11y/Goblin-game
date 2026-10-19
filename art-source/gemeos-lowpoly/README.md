# Gêmeos em estilo low-poly (fonte, ainda não integrada)

Originais gerados por IA, em 1200×880, comprimidos sem perda. **Não são os sprites do jogo.**
Os sprites usados pelo jogo continuam em `assets/sprites/raid/` (pixel art 56×36) até a etapa de corte e integração.
Esta pasta tem 82 PNGs (~80 MB): 41 da Mandíbula e 41 das Patas. Guardar os originais no Git foi decidido com o usuário, mas essa decisão ainda não está confirmada para o total.

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
| Repouso | `idle: 4` | `patas_idle_0..4` (5) | Escolhidos 4: `idle_0`, `idle_2`, `idle_3`, `idle_4`. `idle_1` fica de fora (brilho isolado na pata). Conferir no jogo |
| Caminhada | `walk: 16` | `patas_walk_key_0..7` (8 de 8) + `patas_walk_mid_0..7` (8 de 8) | **Completa, 16 de 16, mas ainda não conferida em ampliação quadro a quadro.** `key_0` e `mid_0..3` são v9 e `mid_4..7` são v10, sem sombra, sem linha de chão e sem tom roxo na medição |
| Dano | `hurt: 3` | `patas_hurt_0..2` | Aceito |
| Ataque | `attack: 9` | `patas_atk_0..8` | Aceito com ressalva. `atk_2`, `atk_4` e `atk_5` refeitos. `atk_4` v12 tem exatamente duas patas de aço (uma terceira pata foi removida), mas a pose ficou menos de ataque: sem boca aberta. Conferir no jogo |
| Morte | `death: 7` | `patas_death_0..6` | Pendente de aprovação final. `death_3` v13a, `death_4` v12, `death_5` v12 e `death_6` v13 (sem sombra; só uma perna de aço visível de perfil, conferir). `death_0..2` antigos, sem reconferência em ampliação |

## Mandíbula v2/v7 (mandíbula de aço grande e visível, também com a boca fechada; pernas sem aço)
A v1 tinha mandíbula pequena e não aparecia com a boca fechada. A v2 foi refeita a partir dela; os quadros da v1 foram removidos.

| Conjunto | Código | Arquivos aqui | Estado |
|---|---|---|---|
| Base | — | `mandibula_base_v2.png` (= `mandibula_v2_idle_0`) | Aceita |
| Repouso | `idle: 5` | `mandibula_v2_idle_0..4` (5 de 5) | Aceito |
| Caminhada | `walk: 16` | `mandibula_v2_walk_key_0..7` + `mandibula_v2_walk_mid_0..7` (16 de 16) | Quadros-chave: `key_0,4,5,6` são v7; `key_1,2,3,7` são v2. Intermediários `mid_N` entre `key_N` e `key_N+1` (o último fecha em `key_0`). Conferidos em folha, não em ampliação quadro a quadro |
| Dano | `hurt: 3` | `mandibula_v2_hurt_0..2` (3 de 3) | Aceito |
| Ataque | `attack: 9` | `mandibula_v2_atk_0..8` (9 de 9) | Aceito. `atk_3` v4, `atk_4` v7, `atk_5` v3, demais v2 |
| Morte | `death: 7` | `patas_death_0..6` | Pendente de aprovação final. `death_3` v13a, `death_4` v12, `death_5` v12 e `death_6` v13 (sem sombra; só uma perna de aço visível de perfil, conferir). `death_0..2` antigos, sem reconferência em ampliação |

## Descartados (não estão aqui)
- Versões cinzas das Patas (`patas_base_cinza`, `patas_key_*`): o usuário pediu o corpo laranja.
- Caminhada de 8 quadros-chave das Patas (`patas_k*`): pata distante fora do chão.
- Mandíbula v1 (base e repouso pequenos): substituída pela v2.
- Versão v3 das Patas e os primeiros quadros de morte e ataque: perdidos no reinício do ambiente.
- Quadros reprovados da v2: `idle_2` antigo (cabeça alta), `atk_3` antigo (bloco de pedra na boca), `atk_4` antigo (duas cabeças), `atk_5` antigo (corpo longo e fino).
- Mandíbula v4/v5 usadas antes: `atk_4` v5 e `death_3` v5 (sombra de chão), `death_3` v6 (substituído pela v7), `death_6` v4 e `atk_3` v4 (aceitos, ainda usados).

## Pendências para integrar
1. Patas: escolha de repouso feita (acima); confirmar no jogo.
2. Mandíbula: caminhada completa (16/16). Conferir intermediários em ampliação antes de cortar.
8. Patas caminhada: refazer `walk_key_0` e `mid_0` (sombra); gerar 7 intermediários; conferir sombra de todos.
3. Patas: pernas de aço em ampliação quadro a quadro; caminhada (8 keys e 8 intermediários), depois de aprovar uma base de caminhada.
4. Corte para 56×36 com `tools/cut_gemeos_lowpoly.py` (pés na última linha, máscara por cor de fundo). Teste em lote: 82 quadros cortados, todos com pés na linha 35. **Reprovado para integração:** sombras entram no corte em `death_2` e `death_5`, `atk_4` sai rosado e o aço fino das pernas fica quase preto nos quadros de caminhada. Precisa de ajuste de máscara e conferência de cor antes das folhas de aprovação.
5. Atualizar `js/creatures.js` apenas quando as contagens baterem.
6. Build, testes e conferência no navegador.
7. Decidir com o usuário se os ~64 MB de PNG ficam no Git.

## Efeitos de ataque (nova rodada, aguardando aprovação)
- **Mandíbula, ataque com corte vermelho:** `mandibula_fx_atk_0..8` (9 quadros). Placa de aço só no focinho, pernas laranja normais. Corte vermelho nos quadros 3 a 5. Quadros 0, 1, 2, 3, 5, 7 e 8 vêm da rodada v2; 4 e 6 da v3. Medido: largura do lobo entre 798 e 942 px (base 798), linha dos pés na mesma altura (747 a 759), cor do corpo entre 142 e 148 no verde médio (base 148) no quadro 3, que tem o efeito mais forte.
- **Patas, tapa com efeito de batida:** `patas_fx_slap_0..8` (9 quadros). Duas pernas de aço, sem placa de mandíbula. Impacto (explosão amarela) nos quadros 3 e 4. Quadro 4 ajustado para não alongar o corpo. Quadro 6 refeito com aço visível (medição por cor azulada não pega aço escuro, conferido em imagem).
- Ainda não integrados em `assets/`. Aprovação pendente.
