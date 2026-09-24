// ============================================================
// save.js — Salvar/carregar progresso no localStorage + autosave
//
// ⚠️ SALVAMENTO DESATIVADO DURANTE O DESENVOLVIMENTO:
// o jogo começa do zero a cada partida e nada é gravado.
// Quando tudo estiver pronto, basta trocar SAVE_ENABLED
// para true (o resto do sistema continua intacto).
// ============================================================

const SAVE_ENABLED = false;
const KEY = 'gnome-village-save-v1';

function saveGame(state) {
  if (!SAVE_ENABLED) return;
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch (e) {
    console.warn('[save] Não foi possível salvar:', e);
  }
}

function loadGame() {
  if (!SAVE_ENABLED) return null;   // sempre começa uma vila nova
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    console.warn('[save] Não foi possível carregar:', e);
    return null;
  }
}

function clearGame() {
  try {
    localStorage.removeItem(KEY);
  } catch (e) {
    console.warn('[save] Não foi possível limpar:', e);
  }
}

// Autosave: chama saveGame(getState()) a cada intervalo
function startAutosave(getState, intervalMs = 10000) {
  if (!SAVE_ENABLED) {
    console.log('[save] Salvamento desativado (desenvolvimento).');
    return;
  }
  setInterval(() => saveGame(getState()), intervalMs);
  console.log(`[save] Autosave ativo (a cada ${intervalMs / 1000}s).`);
}

module.exports = { SAVE_ENABLED, saveGame, loadGame, clearGame, startAutosave };
