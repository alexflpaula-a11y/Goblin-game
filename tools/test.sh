#!/usr/bin/env bash
# test.sh — Roda a bateria completa de testes do jogo.
#
#   1. smoke        lógica pura (vila, goblins, missões, cozinha)
#   2. render       as 6 telas desenham sem erro, traduções e sprites
#   3. playthrough  uma partida inteira: o ciclo do jogo fecha?
#   4. build        o arquivo único distribuído funciona sozinho
#
# Uso:  bash tools/test.sh
set -u
cd "$(dirname "$0")/.."

fails=0
for t in smoke render playthrough gear build; do
  printf '\n\033[1m── %s ─────────────────────────────\033[0m\n' "$t"
  # PIPESTATUS preserva o código de saída do node (o grep mascararia)
  node "tools/${t}_test.mjs" 2>&1 | grep -v '^\['
  if [ "${PIPESTATUS[0]}" -ne 0 ]; then
    fails=$((fails + 1))
  fi
done

printf '\n────────────────────────────────────\n'
if [ "$fails" -eq 0 ]; then
  printf '\033[32mtodas as suítes passaram\033[0m\n'
else
  printf '\033[31m%s suíte(s) falharam\033[0m\n' "$fails"
  exit 1
fi
