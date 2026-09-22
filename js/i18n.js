// ============================================================
// i18n.js — Sistema de idiomas (PT-BR / EN)
// Os textos ficam em assets/data/i18n.*.json.
// Uso: i18n.t('chave', { parametro: valor })
// ============================================================

const FILES = {
  'pt-BR': 'assets/data/i18n.pt-br.json',
  'en': 'assets/data/i18n.en.json',
};

const DICTS = {};

const i18n = {
  lang: 'pt-BR',

  setLang(lang) {
    if (FILES[lang]) this.lang = lang;
  },

  // Traduz uma chave, com interpolação {nome}
  t(key, params) {
    const dict = DICTS[this.lang] || {};
    let s = dict[key] ?? key;
    if (params) {
      for (const k in params) {
        s = s.replace(`{${k}}`, String(params[k]));
      }
    }
    return s;
  },
};

async function loadI18n() {
  if (window.EMBEDDED?.i18n) {
    for (const [lang, dict] of Object.entries(window.EMBEDDED.i18n)) DICTS[lang] = dict;
    console.log('[i18n] dicionários embutidos:', Object.keys(DICTS).join(', '));
    return;
  }
  await Promise.all(
    Object.keys(FILES).map(async (lang) => {
      try {
        const res = await fetch(FILES[lang]);
        DICTS[lang] = await res.json();
      } catch (e) {
        console.warn(`[i18n] Falha ao carregar ${FILES[lang]}`);
        DICTS[lang] = {};
      }
    })
  );
  console.log('[i18n] Dicionários carregados:', Object.keys(DICTS).join(', '));
}

module.exports = { i18n, loadI18n };
