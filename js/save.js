// ============================================================
// save.js — Salvar/carregar progresso no localStorage + autosave
// ============================================================

const KEY = 'gnome-village-save-v1';

function saveGame(state) {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch (e) {
    console.warn('[save] Não foi possível salvar:', e);
  }
}

function loadGame() {
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
  setInterval(() => saveGame(getState()), intervalMs);
  console.log(`[save] Autosave ativo (a cada ${intervalMs / 1000}s).`);
}

module.exports = { saveGame, loadGame, clearGame, startAutosave };
