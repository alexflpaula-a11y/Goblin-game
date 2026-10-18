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


## Mandíbula v2 (mandíbula de aço grande e visível, também com a boca fechada; pernas sem aço)
A v1 tinha mandíbula pequena e não aparecia com a boca fechada. A v2 foi refeita a partir dela; os quadros da v1 foram removidos.

| Conjunto | Código | Arquivos aqui | Estado |
|---|---|---|---|
| Base | — | `mandibula_base_v2.png` (= `mandibula_v2_idle_0`) | Aceita |
| Repouso | `idle: 5` | `mandibula_v2_idle_0`, `_1`, `_3`, `_4` (4 de 5) | `idle_2` reprovado 2 vezes (cabeça alta, pescoço esticado): pendente |
| Caminhada | `walk: 16` | nenhum | Pausada |
| Dano | `hurt: 3` | `mandibula_v2_hurt_0..2` (3) | Aceito (3 de 3) |
| Ataque | `attack: 9` | `mandibula_v2_atk_0..3`, `_6..8` (7 de 9) | `atk_4` (cabeça grande, juba de frente) e `atk_5` (corpo longo e fino) reprovados: pendente |
| Morte | `death: 7` | `mandibula_v2_death_0` (1 de 7) | Em andamento: faltam `death_1..6` |

## Descartados (não estão aqui)
- Versões cinzas das Patas (`patas_base_cinza`, `patas_key_*`): o usuário pediu o corpo laranja.
- Caminhada de 8 quadros-chave das Patas (`patas_k*`): pata distante fora do chão.
- Mandíbula v1 (base e repouso pequenos): substituída pela v2.
- Versão v3 das Patas e os primeiros quadros de morte e ataque: perdidos no reinício do ambiente.
- Quadros reprovados da v2 (`idle_2`, `atk_4`, `atk_5`): não estão aqui.

## Pendências para integrar
1. Patas: escolher 4 quadros de repouso (os 5 atuais estão aqui).
2. Mandíbula: refazer `idle_2`, `atk_4` e `atk_5`; gerar `death_1..6` (6).
3. Caminhada das duas (16 cada), pausada.
4. Corte com `cutlib` para 56×36, pés na linha 36, e medições.
5. Atualizar `js/creatures.js` apenas quando as contagens baterem.
6. Build, testes e conferência no navegador.
