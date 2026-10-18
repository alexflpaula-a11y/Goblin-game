# Gêmeos em estilo low-poly (fonte, ainda não integrada)

Originais gerados por IA, em 1200×880, comprimidos sem perda. **Não são os sprites do jogo.**
Os sprites usados pelo jogo continuam em `assets/sprites/raid/` (pixel art 56×36) até a etapa de corte e integração.

Corpo: lobo normal em laranja-acastanhado, com os mesmos tons do lobo. Mandíbula e Patas são o lobo com a peça de aço.

## Patas (duas patas dianteiras de aço com duas garras cada)
| Conjunto | Código (`js/creatures.js`) | Arquivos aqui | Estado |
|---|---|---|---|
| Base | — | `patas_base_laranja.png` | Aceita |
| Repouso | `idle: 4` | `patas_idle_0..4` (5) | Pendente: escolher 4 para bater com o código |
| Caminhada | `walk: 16` | nenhum | Pausada (poses com a pata distante fora do modelo) |
| Dano | `hurt: 3` | `patas_hurt_0..2` | Aceito |
| Ataque | `attack: 9` | `patas_atk_0..8` | Aceito; `atk_5` com pata mais esticada, conferir no jogo |
| Morte | `death: 7` | `patas_death_0..6` | Aceito; `death_3` e `death_4` refeitos |

## Mandíbula (mandíbula de aço com dentes, pernas sem aço)
| Conjunto | Código | Arquivos aqui | Estado |
|---|---|---|---|
| Base | — | `mandibula_base_laranja.png` | Aceita |
| Repouso | `idle: 5` | `mandibula_idle_1` (1 de 4) | Incompleta: faltam `idle_2..4` |
| Caminhada | `walk: 16` | nenhum | Pausada |
| Dano | `hurt: 3` | nenhum | Não gerada |
| Ataque | `attack: 9` | nenhum | Não gerada |
| Morte | `death: 7` | nenhum | Não gerada |

## Descartados (não estão aqui)
- Versões cinzas das Patas (`patas_base_cinza`, `patas_key_*`): o usuário pediu o corpo laranja.
- Caminhada de 8 quadros-chave (`patas_k*`): pata distante fora do chão.
- Versão v3 e os primeiros quadros de morte e ataque: perdidos no reinício do ambiente.

## Pendências para integrar
1. Mandíbula: repouso (3), dano (3), ataque (9), morte (7).
2. Caminhada das duas (16 cada), pausada.
3. Corte com `cutlib` para 56×36, pés na linha 36, e medições.
4. Atualizar `js/creatures.js` apenas quando as contagens baterem.
5. Build, testes e conferência no navegador.
