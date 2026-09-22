// ============================================================
// balance.js — Carrega o balance.json (todos os números do jogo)
// ============================================================
const BAL = {};

async function loadBalance() {
  if (window.EMBEDDED?.balance) {
    Object.assign(BAL, window.EMBEDDED.balance);
    return BAL;
  }
  try {
    const res = await fetch('assets/data/balance.json');
    Object.assign(BAL, await res.json());
  } catch (e) {
    console.warn('[balance] Falha ao carregar balance.json');
  }
  return BAL;
}

module.exports = { BAL, loadBalance };
