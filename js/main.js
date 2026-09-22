// ============================================================
// main.js — Boot + game loop + roteamento de telas
// Etapa 1.1: entidade goblin, habitação, recrutamento 1-de-3
// ============================================================
const { CONFIG } = require('config.js');
const { Input } = require('input.js');
const { loadAssets, getSprite } = require('assetLoader.js');
const { i18n, loadI18n } = require('i18n.js');
const { saveGame, loadGame, startAutosave } = require('save.js');
const { Camera } = require('camera.js');
const { World, WORLD } = require('world.js');
const { Village } = require('village.js');
const { Nodes } = require('nodes.js');
const { UI } = require('ui.js');
const { loadBalance, BAL } = require('balance.js');
const { Goblin, ATTRS } = require('goblin.js');
// ---------- DOM ----------
const viewport = document.getElementById('viewport');
const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');

const langBtn = document.getElementById('langBtn');
const titleEl = document.getElementById('title');
const subtitleEl = document.getElementById('subtitle');
const statusEl = document.getElementById('status');

// ---------- Estado ----------
const saved = loadGame() || {};
const state = {
  language: saved.language || 'pt-BR',
  taps: saved.taps || 0,
  screen: 'world',        // world | build | recruit | roster | detail
  buildTab: 0,            // 0 estruturas | 1 melhorias
  candidates: null,       // 3 goblins p/ recrutamento
  detailIdx: 0,
  toast: null,            // {msg, until}
};

// ---------- Mundo / vila / câmera / UI ----------
const world = new World(7);
const village = new Village(saved.village);
world.setGoblinCount(village.goblins.length);
const nodes = new Nodes(world, saved.nodes);

const camera = new Camera(
  WORLD.W, WORLD.H,
  saved.cam?.x ?? WORLD.W / 2,
  saved.cam?.y ?? WORLD.H / 2,
  saved.cam?.zoom ?? 1.6
);
const ui = new UI(ctx);
const input = new Input(canvas);

const RARITY_COLOR = { common: '#b9aedc', uncommon: '#4fa562', rare: '#4a90d8', epic: '#d98ae8' };

// Catálogo de estruturas da Casa de Construção (novas aparecem aqui)
const BUILD_DEFS = [
  { id: 'house', sprite: 'building_house_1', lv: 1 },
  { id: 'serraria', lv: 2 }, { id: 'fazenda', lv: 2 },
  { id: 'cozinha', lv: 3 }, { id: 'mercado', lv: 3 },
  { id: 'mina', lv: 4 }, { id: 'estabulo', lv: 4 },
  { id: 'ferraria', lv: 5 }, { id: 'altar', lv: 6 },
  { id: 'bazar', lv: 6 }, { id: 'porto', lv: 7 }, { id: 'quartel', lv: 8 },
];
const BUILD_PANEL = { x: 56, y: 34, w: 528, h: 312 };

// ---------- Escala ----------
let scaleFactor = 1;
let fps = 60, frames = 0, fpsTimer = 0;

function resize() {
  const vw = window.innerWidth, vh = window.innerHeight;
  const dpr = Math.min(window.devicePixelRatio || 1, CONFIG.MAX_DPR);
  const scale = CONFIG.SCALE_MODE === 'cover'
    ? Math.max(vw / CONFIG.LOGICAL_WIDTH, vh / CONFIG.LOGICAL_HEIGHT)
    : Math.min(vw / CONFIG.LOGICAL_WIDTH, vh / CONFIG.LOGICAL_HEIGHT);
  const displayW = Math.round(CONFIG.LOGICAL_WIDTH * scale);
  const displayH = Math.round(CONFIG.LOGICAL_HEIGHT * scale);
  viewport.style.width = displayW + 'px';
  viewport.style.height = displayH + 'px';
  viewport.style.left = (vw - displayW) / 2 + 'px';
  viewport.style.top = (vh - displayH) / 2 + 'px';
  canvas.width = Math.round(displayW * dpr);
  canvas.height = Math.round(displayH * dpr);
  scaleFactor = canvas.width / CONFIG.LOGICAL_WIDTH;
}

// ---------- Coleta (nós finitos) ----------
function handleChop(node, goblin) {
  if (node.depleted) return;
  node.stock -= 1;
  let yield_ = 1;
  if (goblin?.specialty === 'worker' && Math.random() < 0.35) yield_ += 1;
  const key = node.type === 'tree' ? 'wood' : 'stone';
  village.res[key] += yield_;
  world.floats.push({
    x: node.x, y: node.y - 36, ttl: 1.3,
    text: `+${yield_} ${i18n.t('res.' + key)}`,
    color: key === 'wood' ? '#e8c476' : '#cdd3de',
  });
  if (node.stock <= 0) {
    node.depleted = true;
    node.worker = null;
  }
}

// ---------- Toast ----------
function toast(key, params) {
  state.toast = { msg: i18n.t(key, params), until: performance.now() + 2600 };
}

// ---------- Ações ----------
function openRecruit() {
  state.candidates = Goblin.candidates(village.recruitedCount, village.goblins.map((g) => g.name));
  state.screen = 'recruit';
}

function routeTap(id) {
  switch (id) {
    case 'close': state.screen = 'world'; break;
    case 'build_btn': state.screen = 'build'; break;
    case 'close_build': state.screen = 'world'; break;
    case 'tab_0': state.buildTab = 0; break;
    case 'tab_1': state.buildTab = 1; break;
    case 'roster_btn': state.screen = 'roster'; break;
    case 'back_roster': state.screen = 'roster'; break;
    case 'back_world': state.screen = 'world'; break;
    case 'build_house':
      if (village.goblins.length >= village.capacity && false) break;
      if (village.buildHouse()) {
        world.setGoblinCount(village.goblins.length); // casa vazia aparece já já
        toast('toast.built');
        openRecruit();
      } else toast('toast.need');
      break;
    case 'upgrade_house':
      if (village.upgradeHouse(state.upgradeIdx || 0)) {
        toast('toast.upgraded');
        openRecruit();
      } else toast('toast.need');
      break;
    default:
      if (id?.startsWith('bcard_')) {
        const def = BUILD_DEFS.find((d) => d.id === id.slice(6));
        if (!def) break;
        if (def.lv > village.level) { toast('toast.village_level', { n: def.lv }); break; }
        if (def.id === 'house') {
          if (village.nextSlot >= 12) { toast('toast.no_slots'); break; }
          if (village.buildHouse()) { toast('toast.built'); openRecruit(); }
          else toast('toast.need');
        }
        break;
      }
      if (id?.startsWith('card_')) {
        const g = state.candidates[Number(id.slice(5))];
        if (g && village.recruit(g)) {
          world.setGoblinCount(village.goblins.length);
          toast('toast.recruited', { name: g.name });
        }
        state.candidates = null;
        state.screen = 'world';
      } else if (id?.startsWith('up_')) {
        state.upgradeIdx = Number(id.slice(3));
        routeTap('upgrade_house');
      } else if (id?.startsWith('g_')) {
        state.detailIdx = Number(id.slice(2));
        state.screen = 'detail';
      }
  }
}

// ---------- Update ----------
function update(dt) {
  const g = input.consume();

  if (state.screen === 'world') {
    if (g.pan) camera.panByScreen(g.pan.dx, g.pan.dy);
    if (g.pinch) camera.zoomAt(g.pinch.mx, g.pinch.my, g.pinch.factor);
    if (g.wheel) camera.zoomAt(g.wheel.x, g.wheel.y, g.wheel.factor);
    if (g.tap) {
      const uiHit = ui.hit(g.tap);
      if (uiHit) { routeTap(uiHit); return; }
      const w = camera.screenToWorld(g.tap.x, g.tap.y);
      // tocar em goblin trabalhando → chamar de volta
      for (const wk of world.goblins) {
        if (wk.job && Math.abs(w.x - wk.x) < 12 && Math.abs(w.y - (wk.y - 14)) < 20) {
          wk.job.node.worker = null;
          wk.job = null;
          wk.wait = 0.3;
          toast('toast.recalled');
          return;
        }
      }
      const node = nodes.hitTest(w.x, w.y);
      if (node) {
        if (node.worker != null) toast('toast.node_busy');
        else if (!nodes.assign(node, world.goblins)) toast('toast.no_idle');
        return;
      }
      const s = village.hitTest(w.x, w.y);
      if (s) {
        if (s.type === 'construction') state.screen = 'build';
        else if (s.type === 'house') state.screen = 'roster';
        else toast('toast.quest_soon');
      }
    }
  } else if (g.tap) {
    const uiHit = ui.hit(g.tap);
    if (uiHit) routeTap(uiHit);
    else if (state.screen === 'build') {
      const P = BUILD_PANEL;
      if (g.tap.x < P.x || g.tap.x > P.x + P.w || g.tap.y < P.y || g.tap.y > P.y + P.h) {
        state.screen = 'world';
      }
    }
  }

  world.update(dt, {
    village,
    onChop: handleChop,
    workPeriod: BAL.nodes?.workPeriod ?? 1.2,
  });
}

// ---------- Render ----------
function render(time) {
  ctx.imageSmoothingEnabled = false;
  ctx.setTransform(scaleFactor, 0, 0, scaleFactor, 0, 0);
  ctx.fillStyle = '#0d2b47';
  ctx.fillRect(0, 0, CONFIG.LOGICAL_WIDTH, CONFIG.LOGICAL_HEIGHT);

  camera.applyTransform(ctx, scaleFactor);
  world.draw(ctx, time, camera.visible(), [...village.drawList(), ...nodes.drawList()]);

  ctx.setTransform(scaleFactor, 0, 0, scaleFactor, 0, 0);
  drawOverlay(time);

  ui.begin();
  if (state.screen === 'build') drawBuildScreen();
  else if (state.screen === 'recruit') drawRecruitScreen();
  else if (state.screen === 'roster') drawRosterScreen();
  else if (state.screen === 'detail') drawDetailScreen();
  if (state.screen === 'world') drawWorldButtons();
}

function drawOverlay(time) {
  // caixa FPS/zoom
  ctx.textAlign = 'left';
  ctx.font = '10px monospace';
  ctx.fillStyle = 'rgba(0,0,0,0.45)';
  ctx.fillRect(6, 42, 92, 30);
  ctx.fillStyle = '#cfe3ff';
  ctx.fillText('FPS ' + fps, 12, 54);
  ctx.fillText(i18n.t('demo.zoom', { z: camera.zoom.toFixed(1) }), 12, 66);

  // recursos no topo (5 tipos)
  const res = [['wood', village.res.wood], ['stone', village.res.stone], ['ore', village.res.ore], ['food', village.res.food], ['gold', village.res.gold]];
  ctx.font = 'bold 11px monospace';
  let rx = 632;
  for (let i = res.length - 1; i >= 0; i--) {
    const [k, v] = res[i];
    const label = String(v);
    const wLab = ctx.measureText(label).width;
    rx -= wLab;
    ctx.fillStyle = '#ffe9a8';
    ctx.textAlign = 'left';
    ctx.fillText(label, rx, 54);
    rx -= 16;
    ctx.drawImage(getSprite('res_' + k), rx, 44, 14, 14);
    rx -= 10;
  }

  // hint + etiqueta da fase
  if (state.screen === 'world') {
    ctx.textAlign = 'center';
    ctx.fillStyle = 'rgba(0,0,0,0.45)';
    ctx.fillRect(160, 338, 320, 16);
    ctx.fillStyle = '#e8e2f7';
    ctx.font = '9px monospace';
    ctx.fillText(i18n.t('demo.hint'), 320, 346);
  }
  ctx.textAlign = 'left';
  ctx.font = '8px monospace';
  ctx.fillStyle = 'rgba(233,226,247,0.6)';
  ctx.fillText(i18n.t('stage'), 112, 348);

  // toast
  if (state.toast) {
    if (performance.now() > state.toast.until) state.toast = null;
    else {
      ctx.textAlign = 'center';
      ctx.font = 'bold 12px monospace';
      const w = ctx.measureText(state.toast.msg).width + 24;
      ctx.fillStyle = 'rgba(22,16,36,0.92)';
      ctx.fillRect(320 - w / 2, 74, w, 26);
      ctx.strokeStyle = 'rgba(167,139,250,0.7)';
      ctx.strokeRect(320 - w / 2, 74, w, 26);
      ctx.fillStyle = '#efeafd';
      ctx.fillText(state.toast.msg, 320, 87);
    }
  }
}

function drawWorldButtons() {
  // botão rústico de CONSTRUIR no canto inferior esquerdo
  ui.rusticPanel(8, 316, 96, 36);
  ctx.fillStyle = '#9aa0ad'; ctx.fillRect(20, 326, 12, 6);
  ctx.fillStyle = '#6e4626'; ctx.fillRect(24, 332, 4, 12);
  ui.text(58, 334, i18n.t('ui.build_btn'), { align: 'center', size: 11, bold: true, color: '#ffe9b8' });
  ui.region('build_btn', 8, 316, 96, 36);

  ui.button('roster_btn', 548, 316, 84, 34,
    `${i18n.t('ui.village_btn')} ${village.goblins.length}/${village.capacity}`, true, true);
}

// ---------- Tela: Casa de Construção (painel rústico c/ abas) ----------
function drawBuildScreen() {
  const P = BUILD_PANEL;
  ui.rusticPanel(P.x, P.y, P.w, P.h);
  ui.woodSign(P.x + 8, P.y + 6, P.w - 46, 22, i18n.t('ui.build_title'), 12);
  ui.closeX('close_build', P.x + P.w - 28, P.y + 8);

  ui.tab('tab_0', P.x + 14, P.y + 34, 130, 20, i18n.t('ui.tab_structures'), state.buildTab === 0);
  ui.tab('tab_1', P.x + 152, P.y + 34, 110, 20, i18n.t('ui.tab_upgrades'), state.buildTab === 1);

  if (state.buildTab === 0) drawStructureCards(P);
  else drawUpgradeRows(P);
}

function drawStructureCards(P) {
  const vLv = village.level;
  const visible = BUILD_DEFS.filter((d) => d.lv <= vLv + 2).slice(0, 5);
  const slots = [...visible];
  if (slots.length < 6) slots.push({ id: '__soon', lv: 0 });

  slots.forEach((def, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = P.x + 10 + col * 172, y = P.y + 60 + row * 122;
    const w = 164, h = 118;
    ui.parchment(x, y, w, h);

    if (def.id === '__soon') {
      ctx.fillStyle = 'rgba(60,39,18,0.35)';
      ctx.fillRect(x + 1, y + 1, w - 2, h - 2);
      ui.text(x + w / 2, y + h / 2, i18n.t('ui.more_soon'), { align: 'center', size: 10, color: '#8a6b4a' });
      return;
    }

    ui.woodSign(x + 4, y + 3, w - 8, 14, i18n.t('bld.' + def.id), 8);
    const cx = x + w / 2;
    const locked = def.lv > vLv;

    if (!locked) {
      ui.glow(cx, y + 62, 34);
      if (def.sprite) ctx.drawImage(getSprite(def.sprite), cx - 22, y + 40, 44, 44);
      if (def.id === 'house') {
        ui.text(x + 6, y + h - 9, i18n.t('ui.built_count', { n: village.houses.length, max: 12 }), { size: 8, bold: true, color: '#6e4626' });
      }
      const cost = village.houseBuildCost();
      let rx = x + w - 8;
      for (const [k, v] of Object.entries(cost).reverse()) {
        const label = String(v);
        ctx.font = 'bold 9px monospace';
        const lw = ctx.measureText(label).width;
        rx -= lw;
        ui.text(rx, y + h - 9, label, { size: 9, bold: true, color: village.res[k] >= v ? '#4a3018' : '#8c2f1f' });
        rx -= 13;
        ctx.drawImage(getSprite('res_' + k), rx, y + h - 15, 11, 11);
        rx -= 5;
      }
      ui.region('bcard_' + def.id, x, y, w, h);
    } else {
      ctx.fillStyle = 'rgba(30,20,10,0.55)';
      ctx.fillRect(x + 1, y + 18, w - 2, h - 19);
      ctx.fillStyle = '#3c2712';
      ctx.fillRect(cx - 18, y + 38, 36, 36);
      ctx.strokeStyle = '#2a1b0c'; ctx.lineWidth = 1.5;
      ctx.strokeRect(cx - 18, y + 38, 36, 36);
      ui.text(cx, y + 56, '?', { align: 'center', size: 18, bold: true, color: '#8a6b4a' });
      ui.text(cx, y + h - 10, i18n.t('ui.locked_village', { n: def.lv }), { align: 'center', size: 8, bold: true, color: '#ffb8a8' });
      ui.region('bcard_' + def.id, x, y, w, h);
    }
  });
}

function drawUpgradeRows(P) {
  ui.text(P.x + 16, P.y + 64, i18n.t('ui.upgrade_section'), { size: 10, bold: true, color: '#ffe9b8' });
  village.houses.slice(0, 3).forEach((h, i) => {
    const y = P.y + 76 + i * 62;
    ui.parchment(P.x + 10, y, P.w - 20, 54);
    ui.text(P.x + 22, y + 15, `${i18n.t('ui.house_n', { n: i + 1 })} • ${i18n.t('ui.level', { n: h.level })}`, { size: 11, bold: true, color: '#4a3018' });
    const maxed = h.level >= (BAL.house?.maxLevel ?? 3);
    const cost = village.houseUpgradeCost(h);
    ui.text(P.x + 22, y + 36, maxed ? i18n.t('ui.max') : village.costText(cost, (k) => i18n.t(k)), { size: 9, color: '#6e4626' });
    ui.button('up_' + i, P.x + P.w - 100, y + 12, 78, 28,
      maxed ? i18n.t('ui.max') : i18n.t('ui.upgrade_house'),
      !maxed && village.canAfford(cost));
  });
  if (village.houses.length > 3) {
    ui.text(P.x + 16, P.y + 76 + 3 * 62 + 8, `+${village.houses.length - 3} …`, { size: 9, color: '#ffe9b8' });
  }
}

// ---------- Tela: Recrutamento (escolher 1 de 3) ----------
function drawRecruitScreen() {
  ui.rusticPanel(8, 40, 624, 280);
  ui.woodSign(16, 46, 280, 22, i18n.t('ui.recruit_title'), 11);
  ui.text(310, 57, i18n.t('ui.recruit_sub', { n: village.goblins.length, cap: village.capacity }), { size: 9, color: '#ffe9b8' });

  (state.candidates || []).forEach((g, i) => {
    const x = 16 + i * 204, y = 74, w = 200, h = 236;
    ui.parchment(x, y, w, h);
    ui.region('card_' + i, x, y, w, h);
    const cx = x + w / 2;
    ui.glow(cx, y + 44, 36);
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(getSprite(`goblin_idle_${i % 5}`), cx - 28, y + 16, 56, 56);

    ui.text(cx, y + 84, g.name, { align: 'center', size: 12, bold: true, color: '#3c2712' });
    ui.text(cx, y + 100, `${i18n.t('spec.' + g.specialty)} • ${i18n.t('rarity.' + g.rarity)} ${'★'.repeat(RARITIES_IDX(g.rarity) + 1)}`,
      { align: 'center', size: 9, color: '#6e4626' });

    ATTRS.forEach((a, ai) => {
      const col = ai % 2, row = Math.floor(ai / 2);
      const bx = x + 12 + col * 100, by = y + 122 + row * 24;
      ui.text(bx, by, i18n.t('attr.short.' + a), { size: 8, color: '#6e4626' });
      ui.bar(bx + 26, by - 4, 46, 8, g[a] / 10, RARITY_COLOR[g.rarity]);
      ui.text(bx + 76, by, String(g[a]), { size: 8, bold: true, color: '#3c2712' });
    });
    ui.text(cx, y + h - 12, i18n.t('ui.recruit_pick'), { align: 'center', size: 8, color: '#8a6b4a' });
  });
}
function RARITIES_IDX(r) { return ['common', 'uncommon', 'rare', 'epic'].indexOf(r); }

// ---------- Tela: Roster ----------
function drawRosterScreen() {
  ui.rusticPanel(8, 40, 624, 286);
  ui.woodSign(16, 46, 300, 22, i18n.t('ui.roster_title', { n: village.goblins.length, cap: village.capacity }), 11);
  village.goblins.slice(0, 6).forEach((g, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 16 + col * 308, y = 76 + row * 60, w = 300, h = 56;
    ui.parchment(x, y, w, h);
    ui.region('g_' + i, x, y, w, h);
    ctx.drawImage(getSprite('goblin_idle_0'), x + 8, y + 10, 36, 36);
    ui.text(x + 52, y + 16, `${g.name}  ${i18n.t('ui.level', { n: g.level })}`, { size: 11, bold: true, color: '#3c2712' });
    ui.text(x + 52, y + 34, `${i18n.t('spec.' + g.specialty)} • ${i18n.t('rarity.' + g.rarity)}`, { size: 9, color: '#6e4626' });
    ui.bar(x + 212, y + 14, 78, 8, g.hp / g.maxHp, '#4fa562');
    ui.text(x + 212, y + 34, `HP ${g.hp}/${g.maxHp}`, { size: 8, color: '#6e4626' });
  });
  if (village.goblins.length > 6) {
    ui.text(560, 76 + 3 * 60 + 6, `+${village.goblins.length - 6} …`, { size: 9, color: '#ffe9b8' });
  }
  ui.button('back_world', 272, 298, 96, 24, i18n.t('ui.close'), true, true);
}

// ---------- Tela: Detalhe do goblin ----------
function drawDetailScreen() {
  const g = village.goblins[state.detailIdx];
  if (!g) { state.screen = 'roster'; return; }
  ui.rusticPanel(60, 40, 520, 286);
  ui.woodSign(70, 48, 220, 22, g.name, 12);
  ui.glow(130, 130, 46);
  ctx.drawImage(getSprite('goblin_idle_0'), 94, 84, 72, 72);
  ui.text(94, 172, i18n.t('spec.' + g.specialty), { size: 11, bold: true, color: '#ffe9b8' });
  ui.text(94, 188, `${i18n.t('rarity.' + g.rarity)} ${'★'.repeat(RARITIES_IDX(g.rarity) + 1)}`, { size: 9, color: '#ffe9b8' });
  ui.text(94, 204, i18n.t('ui.level', { n: g.level }), { size: 10, color: '#ffe9b8' });
  ui.bar(94, 212, 140, 8, g.xp / g.xpNext(), '#e8b23a');

  ATTRS.forEach((a, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const ax = 250 + col * 165, ay = 84 + row * 36;
    ui.text(ax, ay, i18n.t('attr.' + a), { size: 9, color: '#ffe9b8' });
    ui.bar(ax, ay + 8, 120, 9, g[a] / 10, RARITY_COLOR[g.rarity]);
    ui.text(ax + 128, ay + 4, `${g[a]}/10`, { size: 10, bold: true, color: '#efeafd' });
  });

  ui.text(250, 208, `HP ${g.hp}/${g.maxHp}   MP ${g.mp}/${g.maxMp}`, { size: 10, color: '#b9aedc' });
  ui.button('back_roster', 270, 292, 100, 26, i18n.t('ui.back'), true, true);
}

// ---------- Textos DOM ----------
function applyTexts() {
  titleEl.textContent = i18n.t('app.title');
  subtitleEl.textContent = i18n.t('app.subtitle');
  langBtn.textContent = i18n.lang === 'pt-BR' ? 'EN' : 'PT';
  statusEl.textContent =
    `${i18n.t('demo.status', { n: state.taps })}  •  ${i18n.t('demo.autosave')}  •  ${i18n.t('stage')}`;
}

// ---------- Loop ----------
let last = performance.now();
function loop(now) {
  let dt = (now - last) / 1000;
  last = now;
  if (dt > 0.1) dt = 0.1;
  frames += 1; fpsTimer += dt;
  if (fpsTimer >= 0.5) { fps = Math.round(frames / fpsTimer); frames = 0; fpsTimer = 0; }
  update(dt);
  render(now / 1000);
  requestAnimationFrame(loop);
}

// ---------- Boot ----------
langBtn.addEventListener('click', () => {
  i18n.setLang(i18n.lang === 'pt-BR' ? 'en' : 'pt-BR');
  state.language = i18n.lang;
  saveGame(currentSave());
  applyTexts();
});

function currentSave() {
  return {
    language: state.language,
    taps: state.taps,
    cam: { x: camera.x, y: camera.y, zoom: camera.zoom },
    village: village.serialize(),
    nodes: nodes.serialize(),
  };
}

async function init() {
  resize();
  window.addEventListener('resize', resize);
  window.addEventListener('orientationchange', () => setTimeout(resize, 120));

  // pede paisagem no celular (quando o navegador permitir)
  try { screen.orientation?.lock?.('landscape')?.catch?.(() => {}); } catch (e) { /* sem suporte */ }

  i18n.setLang(state.language);
  await loadI18n();
  await loadBalance();
  await loadAssets();

  // ganchos de screenshot (?demo=...)
  const demo = new URLSearchParams(location.search).get('demo');
  if (demo === 'recruit') openRecruit();
  else if (demo === 'roster') state.screen = 'roster';
  else if (demo === 'build') state.screen = 'build';
  else if (demo === 'nodes' || demo === 'work' || demo === 'stumps') {
    const t = nodes.list.find((n) => n.type === 'tree' && !n.depleted);
    if (t) {
      camera.x = t.x; camera.y = t.y + 20; camera.zoom = 1.4;
      if (demo === 'work') {
        const w = nodes.assign(t, world.goblins);
        if (w) { w.x = t.x - 26; w.y = t.y + 8; } // p/ prévia: começa ao lado do nó
      }
      if (demo === 'stumps') {
        let k = 0;
        for (const n of nodes.list) {
          if (Math.hypot(n.x - t.x, n.y - t.y) < 90 && k < 6) { n.depleted = true; n.stock = 0; k++; }
        }
      }
    }
  }

  startAutosave(currentSave, 10000);
  applyTexts();
  requestAnimationFrame(loop);
}

init();
