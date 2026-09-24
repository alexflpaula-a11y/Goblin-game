// ============================================================
// assetLoader.js — Carrega os sprites a partir do manifest.json
// Se um PNG ainda não existir, desenha um PLACEHOLDER automático
// (quadrado colorido + nome) para o jogo nunca quebrar.
// Isso permite que você vá soltando os sprites reais na pasta
// sem precisar mexer no código.
// ============================================================

const cache = new Map();

const CATEGORY_PREFIXES = [
  'gnome', 'building', 'item', 'res', 'node', 'tile',
  'ui', 'enemy', 'boss', 'fx', 'misc',
];

// Carrega o manifest e todos os sprites listados nele.
// Se existir window.EMBEDDED (build de arquivo único), usa os
// data-URIs embutidos em vez de fazer fetch — funciona em file://
async function loadAssets(manifestUrl = 'assets/manifest.json') {
  if (window.EMBEDDED?.sprites) {
    const entries = Object.entries(window.EMBEDDED.sprites);
    await Promise.all(entries.map(([id, src]) => new Promise((resolve) => {
      const img = new Image();
      img.onload = () => { cache.set(id, img); resolve(); };
      img.onerror = () => { cache.set(id, makePlaceholder(id)); resolve(); };
      img.src = src;
    })));
    console.log(`[assetLoader] ${cache.size} sprites embutidos prontos.`);
    return cache;
  }

  let manifest;
  try {
    const res = await fetch(manifestUrl);
    manifest = await res.json();
  } catch (e) {
    console.warn('[assetLoader] Manifest não encontrado — seguindo sem sprites.');
    manifest = { sprites: [] };
  }

  await Promise.all((manifest.sprites || []).map(loadOne));
  console.log(`[assetLoader] ${cache.size} sprites prontos.`);
  return cache;
}

async function loadOne(entry) {
  const id = entry.id;
  const img = new Image();
  try {
    await new Promise((resolve, reject) => {
      img.onload = resolve;
      img.onerror = reject;
      img.src = entry.path;
    });
    cache.set(id, img);
  } catch (e) {
    // Arquivo ainda não existe → placeholder
    cache.set(id, makePlaceholder(id));
  }
}

// Retorna o sprite (real ou placeholder) para desenhar
function getSprite(id) {
  return cache.get(id) || makePlaceholder(id);
}

// ---------------- Placeholders ----------------

function hashHue(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = (h * 31 + str.charCodeAt(i)) >>> 0;
  }
  return h % 360;
}

// Extrai um rótulo curto legível: "gnome_warrior_idle_0" → "WAR"
function shortLabel(id) {
  const parts = id.split('_');
  let label = parts[0];
  if (CATEGORY_PREFIXES.includes(parts[0]) && parts.length > 1) {
    label = parts[1];
  }
  if (/^\d+$/.test(label) && parts.length > 2) {
    label = parts[2];
  }
  return label.slice(0, 3).toUpperCase();
}

function makePlaceholder(id) {
  const size = 32;
  const c = document.createElement('canvas');
  c.width = size;
  c.height = size;
  const g = c.getContext('2d');

  const hue = hashHue(id);
  g.fillStyle = `hsl(${hue}, 65%, 55%)`;
  g.fillRect(0, 0, size, size);

  g.strokeStyle = 'rgba(0,0,0,0.35)';
  g.lineWidth = 1;
  g.strokeRect(0.5, 0.5, size - 1, size - 1);

  g.strokeStyle = 'rgba(255,255,255,0.25)';
  g.beginPath();
  g.moveTo(0, 0);
  g.lineTo(size, size);
  g.stroke();

  g.fillStyle = 'rgba(0,0,0,0.55)';
  g.fillRect(1, size - 9, size - 2, 8);

  g.fillStyle = '#fff';
  g.font = 'bold 7px monospace';
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.fillText(shortLabel(id), size / 2, size - 5);

  return c;
}

module.exports = { loadAssets, getSprite };
