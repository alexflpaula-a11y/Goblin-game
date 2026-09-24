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
const { Village, BUILDINGS, BUILD_ORDER } = require('village.js');
const { Nodes } = require('nodes.js');
const { UI } = require('ui.js');
const { loadBalance, BAL } = require('balance.js');
const { Goblin, ATTRS } = require('goblin.js');
const { Quests } = require('quests.js');
const cooking = require('cooking.js');
const market = require('market.js');
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
  // world | build | recruit | roster | detail | quests | kitchen | market
  screen: 'world',
  buildTab: 0,            // 0 estruturas | 1 melhorias
  buildPage: 0,           // catálogo paginado (12 estruturas)
  candidates: null,       // 3 goblins p/ recrutamento
  detailIdx: 0,
  feedIdx: null,          // prato escolhido p/ alimentar um goblin
  marketTab: 0,           // 0 vender | 1 comprar
  marketPage: 0,          // prateleira paginada
  marketQty: {},          // quantidade escolhida por item ("res:wood" → 3)
  toast: null,            // {msg, until}
  levelUp: null,          // {level, until} — banner de nível da vila
};

// ---------- Mundo / vila / câmera / UI ----------
const world = new World(7);
const village = new Village(saved.village);
world.setGoblinCount(village.goblins.length);
const nodes = new Nodes(world, saved.nodes);
nodes.syncFacilities(village);          // postos da Fazenda/Mina
const quests = new Quests(saved.quests);

const camera = new Camera(
  WORLD.W, WORLD.H,
  saved.cam?.x ?? WORLD.W / 2,
  saved.cam?.y ?? WORLD.H / 2,
  saved.cam?.zoom ?? 1.6
);
const ui = new UI(ctx);
const input = new Input(canvas);

const RARITY_COLOR = { common: '#b9aedc', uncommon: '#4fa562', rare: '#4a90d8', epic: '#d98ae8' };

// Catálogo da Casa de Construção: vem direto do village.js, então
// toda estrutura nova aparece aqui automaticamente.
const BUILD_DEFS = BUILD_ORDER.map((id) => ({
  id, sprite: BUILDINGS[id].sprite, lv: BUILDINGS[id].reqLevel,
}));
const BUILD_PANEL = { x: 56, y: 34, w: 528, h: 312 };
const CARDS_PER_PAGE = 6;

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
// O que cada tipo de posto entrega por ciclo de trabalho.
const NODE_YIELD = {
  tree: { res: 'wood', color: '#e8c476' },
  rock: { res: 'stone', color: '#cdd3de' },
  farm: { res: 'food', color: '#8fd98a' },
  // a mina dá pedra e, às vezes, minério (quanto melhor a mina, mais)
  mineshaft: { res: 'stone', color: '#cdd3de', bonus: { res: 'ore', color: '#b6c2d9' } },
};

function handleChop(node, goblin) {
  if (node.depleted) return;
  const def = NODE_YIELD[node.type] || NODE_YIELD.tree;

  let yield_ = 1;
  // Trabalhador rende o dobro de vez em quando
  if (goblin?.specialty === 'worker' && Math.random() < 0.35) yield_ += 1;
  // Serraria/Mina melhoram o rendimento do recurso correspondente
  if (node.type === 'tree' && village.has('serraria')) {
    if (Math.random() < 0.2 * village.levelOf('serraria')) yield_ += 1;
  }

  let key = def.res;
  let color = def.color;
  // Mina: chance de sair minério em vez de pedra, escalando com o nível
  if (def.bonus && Math.random() < 0.18 + 0.12 * (node.level || 1)) {
    key = def.bonus.res;
    color = def.bonus.color;
  }

  village.add(key, yield_);
  world.floats.push({
    x: node.x, y: node.y - 36, ttl: 1.3,
    text: `+${yield_} ${i18n.t('res.' + key)}`,
    color,
  });

  // Postos infinitos (fazenda/mina) nunca esgotam
  if (node.infinite) return;
  node.stock -= 1;
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

/** Mostra o banner de "vila subiu de nível" e diz o que liberou. */
function celebrateLevelUps(ups) {
  if (!ups) return;
  state.levelUp = { level: village.level, until: performance.now() + 3800 };
  const unlocked = village.unlockedAt(village.level);
  if (unlocked.length) {
    const names = unlocked.map((id) => i18n.t('bld.' + id)).join(', ');
    toast('toast.unlocked', { names });
  }
}

/** Constrói uma estrutura pelo catálogo, com mensagem clara de erro. */
function tryBuild(type) {
  const why = village.blockedReason(type);
  if (why?.reason === 'level') { toast('toast.village_level', { n: why.need }); return; }
  if (why?.reason === 'count') {
    toast(type === 'house' ? 'toast.no_slots' : 'toast.already_built');
    return;
  }
  if (why?.reason === 'cost') { toast('toast.need'); return; }

  const s = village.build(type);
  if (!s) { toast('toast.need'); return; }

  nodes.syncFacilities(village);   // Fazenda/Mina ganham posto de trabalho
  if (type === 'house') {
    world.setGoblinCount(village.goblins.length);
    toast('toast.built');
    openRecruit();                 // casa nova → escolher 1 de 3
  } else {
    toast('toast.built_x', { name: i18n.t('bld.' + type) });
  }
}

// ---------- Mercado (etapa 1.6) ----------
/** Abre a tela do Mercado — só se ele já estiver construído. */
function openMarket() {
  if (!village.has('mercado')) { toast('toast.market_closed'); return; }
  state.screen = 'market';
  state.marketPage = 0;
}

/** "res:wood" → {kind:'res', key:'wood'} */
function slotParts(slot) {
  const [kind, key] = slot.split(':');
  return { kind, key };
}

/** Teto da quantidade: o que dá para vender ou o que o ouro compra. */
function marketLimit(slot) {
  const { kind, key } = slotParts(slot);
  return state.marketTab === 0
    ? market.maxSell(village, kind, key)
    : market.maxBuy(village, kind, key);
}

/** Quantidade escolhida agora (sempre dentro do limite, mínimo 1). */
function marketQty(slot) {
  const limit = marketLimit(slot);
  if (limit <= 0) return 0;
  const q = state.marketQty[slot] ?? 1;
  return Math.max(1, Math.min(limit, q));
}

function marketBumpQty(slot, delta) {
  state.marketQty[slot] = Math.max(1, Math.min(marketLimit(slot), marketQty(slot) + delta));
}

/** Confirma a venda/compra e devolve o recibo em forma de toast. */
function marketConfirm(slot) {
  const { kind, key } = slotParts(slot);
  const qty = marketQty(slot);
  const name = kind === 'meal' ? i18n.t('meal.' + key) : i18n.t('res.' + key);

  if (state.marketTab === 0) {
    const gold = market.sell(village, kind, key, qty);
    if (gold > 0) toast('toast.sold', { n: qty, name, gold });
    else toast('toast.market_nothing');
  } else {
    const cost = market.buy(village, kind, key, qty);
    if (cost > 0) toast('toast.bought', { n: qty, name, gold: cost });
    else toast('toast.market_gold');
  }
  // depois do negócio a quantidade volta ao mínimo
  delete state.marketQty[slot];
}

function routeTap(id) {
  switch (id) {
    case 'close': state.screen = 'world'; break;
    case 'build_btn': state.screen = 'build'; break;
    case 'close_build': state.screen = 'world'; break;
    case 'tab_0': state.buildTab = 0; state.buildPage = 0; break;
    case 'tab_1': state.buildTab = 1; break;
    case 'page_prev': state.buildPage = Math.max(0, state.buildPage - 1); break;
    case 'page_next': state.buildPage += 1; break;
    case 'upage_prev': state.upgradePage = Math.max(0, (state.upgradePage || 0) - 1); break;
    case 'upage_next': state.upgradePage = (state.upgradePage || 0) + 1; break;
    case 'roster_btn': state.screen = 'roster'; break;
    case 'back_roster': state.screen = 'roster'; break;
    case 'back_world': state.screen = 'world'; state.feedIdx = null; break;
    case 'quests_btn': state.screen = 'quests'; break;
    case 'kitchen_btn': state.screen = 'kitchen'; break;
    case 'market_btn': openMarket(); break;
    case 'mtab_0': state.marketTab = 0; state.marketPage = 0; break;
    case 'mtab_1': state.marketTab = 1; state.marketPage = 0; break;
    case 'mpage_prev': state.marketPage = Math.max(0, state.marketPage - 1); break;
    case 'mpage_next': state.marketPage += 1; break;
    case 'build_house': tryBuild('house'); break;
    case 'upgrade_house':
      if (village.upgradeHouse(state.upgradeIdx || 0)) {
        toast('toast.upgraded');
        openRecruit();             // melhorar casa também recruta (§1.1)
      } else toast('toast.need');
      break;
    default:
      // ----- catálogo de construção -----
      if (id?.startsWith('bcard_')) {
        tryBuild(id.slice(6));
        break;
      }
      // ----- melhorar estrutura (aba Melhorias) -----
      if (id?.startsWith('upf_')) {
        const s = village.get(id.slice(4));
        if (!s) break;
        if (s.level >= village.maxUpgradeLevel(s.type)) {
          toast('toast.village_level', { n: s.level + 1 });
        } else if (village.upgrade(s)) {
          nodes.syncFacilities(village);
          toast('toast.upgraded');
        } else toast('toast.need');
        break;
      }
      // ----- entregar missão -----
      if (id?.startsWith('qdo_')) {
        const q = quests.list.find((x) => x.id === Number(id.slice(4)));
        const r = quests.deliver(q, village);
        if (r) {
          toast('toast.quest_done', { gold: r.gold, xp: r.xp });
          celebrateLevelUps(r.levelUps);
        } else toast('toast.quest_missing');
        break;
      }
      // ----- cozinhar -----
      if (id?.startsWith('cook_')) {
        const out = cooking.cook(village, id.slice(5));
        if (out) toast('toast.cooked', { n: out.qty, name: i18n.t('meal.' + out.id) });
        else toast('toast.need');
        break;
      }
      // ----- mercado: +/-, tudo/máx e confirmar -----
      if (id?.startsWith('mq_')) {          // mq_<+|->_<kind>:<key>
        const [, sign, slot] = id.split('_');
        marketBumpQty(slot, sign === '+' ? 1 : -1);
        break;
      }
      if (id?.startsWith('mmax_')) {        // mmax_<kind>:<key>
        const slot = id.slice(5);
        state.marketQty[slot] = marketLimit(slot);
        break;
      }
      if (id?.startsWith('mdo_')) {         // mdo_<kind>:<key>
        marketConfirm(id.slice(4));
        break;
      }
      // ----- escolher prato e alimentar goblin -----
      if (id?.startsWith('pick_')) {
        const mealId = id.slice(5);
        state.feedIdx = state.feedIdx === mealId ? null : mealId;
        break;
      }
      if (id?.startsWith('feed_')) {
        const g = village.goblins[Number(id.slice(5))];
        if (!state.feedIdx) { toast('toast.pick_meal'); break; }
        const healed = cooking.feed(village, g, state.feedIdx);
        if (healed > 0) toast('toast.healed', { name: g.name, n: healed });
        else toast('toast.no_heal');
        if (!village.meals[state.feedIdx]) state.feedIdx = null;
        break;
      }
      // ----- recrutamento / roster -----
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
      // tocar numa estrutura abre a tela dela
      const s = village.hitTest(w.x, w.y);
      if (s) {
        if (s.type === 'construction') state.screen = 'build';
        else if (s.type === 'house') state.screen = 'roster';
        else if (s.type === 'quest') state.screen = 'quests';
        else if (s.type === 'cozinha') state.screen = 'kitchen';
        else if (s.type === 'mercado') openMarket();
        else toast('toast.soon');
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

  // missões renovam sozinhas com o tempo
  quests.update(dt, village.level);

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
  else if (state.screen === 'quests') drawQuestScreen();
  else if (state.screen === 'kitchen') drawKitchenScreen();
  else if (state.screen === 'market') drawMarketScreen();
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

  // ---------- Nível e XP da vila ----------
  const vx = 104;
  const vw = 116;
  ctx.fillStyle = 'rgba(0,0,0,0.45)';
  ctx.fillRect(vx, 42, vw, 30);
  ui.text(vx + 6, 52, i18n.t('ui.village_level', { n: village.level }),
    { size: 10, bold: true, color: '#ffe9a8' });
  const frac = village.xp / village.xpNext();
  ui.bar(vx + 6, 58, vw - 12, 7, frac, '#a78bfa');
  ui.text(vx + vw - 6, 62, `${village.xp}/${village.xpNext()}`,
    { size: 7, align: 'right', color: '#d9cdfa' });

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

  // banner de nível da vila
  if (state.levelUp) {
    if (performance.now() > state.levelUp.until) state.levelUp = null;
    else {
      const msg = i18n.t('ui.level_up', { n: state.levelUp.level });
      ctx.textAlign = 'center';
      ctx.font = 'bold 16px monospace';
      const w = ctx.measureText(msg).width + 40;
      ui.woodSign(320 - w / 2, 108, w, 30, msg, 14);
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

  // MISSÕES — mostra quantas estão prontas para entregar
  const ready = quests.list.filter((q) => q.canDeliver(village)).length;
  ui.rusticPanel(112, 316, 104, 36);
  ui.text(164, 334, i18n.t('ui.quests_btn'),
    { align: 'center', size: 11, bold: true, color: '#ffe9b8' });
  ui.region('quests_btn', 112, 316, 104, 36);
  if (ready > 0) {
    ctx.fillStyle = '#4fa562';
    ctx.beginPath(); ctx.arc(208, 322, 7, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = '#1b1530'; ctx.lineWidth = 1.5; ctx.stroke();
    ui.text(208, 323, String(ready), { align: 'center', size: 9, bold: true, color: '#0f2a16' });
  }

  // COZINHA — só aparece depois de construída
  if (village.has('cozinha')) {
    ui.rusticPanel(224, 316, 100, 36);
    ui.text(274, 334, i18n.t('ui.kitchen_btn'),
      { align: 'center', size: 11, bold: true, color: '#ffe9b8' });
    ui.region('kitchen_btn', 224, 316, 100, 36);
  }

  // MERCADO — só aparece depois de construído
  if (village.has('mercado')) {
    ui.rusticPanel(332, 316, 100, 36);
    ctx.drawImage(getSprite('res_gold'), 342, 326, 14, 14);
    ui.text(392, 334, i18n.t('ui.market_btn'),
      { align: 'center', size: 11, bold: true, color: '#ffe9b8' });
    ui.region('market_btn', 332, 316, 100, 36);
  }

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

/** Desenha uma linha de custo com ícones, alinhada à direita. */
function drawCostRow(cost, xRight, y) {
  let rx = xRight;
  for (const [k, v] of Object.entries(cost || {}).reverse()) {
    const label = String(v);
    ctx.font = 'bold 9px monospace';
    rx -= ctx.measureText(label).width;
    ui.text(rx, y, label, {
      size: 9, bold: true,
      color: (village.res[k] || 0) >= v ? '#4a3018' : '#8c2f1f',
    });
    rx -= 13;
    ctx.drawImage(getSprite('res_' + k), rx, y - 6, 11, 11);
    rx -= 5;
  }
}

function drawStructureCards(P) {
  const vLv = village.level;
  // O catálogo mostra TODAS as estruturas, paginadas de 6 em 6.
  const pages = Math.ceil(BUILD_DEFS.length / CARDS_PER_PAGE);
  state.buildPage = Math.max(0, Math.min(state.buildPage, pages - 1));
  const from = state.buildPage * CARDS_PER_PAGE;
  const slots = BUILD_DEFS.slice(from, from + CARDS_PER_PAGE);

  slots.forEach((def, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = P.x + 10 + col * 172, y = P.y + 60 + row * 122;
    const w = 164, h = 118;
    ui.parchment(x, y, w, h);

    ui.woodSign(x + 4, y + 3, w - 8, 14, i18n.t('bld.' + def.id), 8);
    const cx = x + w / 2;
    const locked = def.lv > vLv;
    const built = village.countOf(def.id);
    const maxCount = BUILDINGS[def.id].maxCount;
    const full = built >= maxCount;

    if (locked) {
      // travada pelo nível da vila → placa "?" + nível exigido
      ctx.fillStyle = 'rgba(30,20,10,0.55)';
      ctx.fillRect(x + 1, y + 18, w - 2, h - 19);
      ctx.fillStyle = '#3c2712';
      ctx.fillRect(cx - 18, y + 38, 36, 36);
      ctx.strokeStyle = '#2a1b0c'; ctx.lineWidth = 1.5;
      ctx.strokeRect(cx - 18, y + 38, 36, 36);
      ui.text(cx, y + 56, '?', { align: 'center', size: 18, bold: true, color: '#8a6b4a' });
      ui.text(cx, y + h - 10, i18n.t('ui.locked_village', { n: def.lv }),
        { align: 'center', size: 8, bold: true, color: '#ffb8a8' });
      ui.region('bcard_' + def.id, x, y, w, h);
      return;
    }

    ui.glow(cx, y + 62, 34);
    ctx.drawImage(getSprite(def.sprite), cx - 22, y + 40, 44, 44);

    if (full) {
      // já construída (e no limite) → selo de concluído
      ctx.fillStyle = 'rgba(30,20,10,0.32)';
      ctx.fillRect(x + 1, y + 18, w - 2, h - 19);
      ui.text(cx, y + h - 10, i18n.t('ui.built_ok'),
        { align: 'center', size: 9, bold: true, color: '#2f6b3c' });
    } else {
      if (maxCount > 1) {
        ui.text(x + 6, y + h - 9, i18n.t('ui.built_count', { n: built, max: maxCount }),
          { size: 8, bold: true, color: '#6e4626' });
      }
      drawCostRow(village.buildCost(def.id), x + w - 8, y + h - 9);
      ui.region('bcard_' + def.id, x, y, w, h);
    }
  });

  // paginação
  if (pages > 1) {
    const py = P.y + P.h - 16;
    if (state.buildPage > 0) ui.button('page_prev', P.x + 210, py - 8, 36, 18, '‹', true);
    ui.text(P.x + 264, py, `${state.buildPage + 1}/${pages}`,
      { align: 'center', size: 9, bold: true, color: '#ffe9b8' });
    if (state.buildPage < pages - 1) ui.button('page_next', P.x + 282, py - 8, 36, 18, '›', true);
  }
}

function drawUpgradeRows(P) {
  ui.text(P.x + 16, P.y + 64, i18n.t('ui.upgrade_section'),
    { size: 10, bold: true, color: '#ffe9b8' });

  // Casas (cada nível = +1 morador) e depois as demais estruturas.
  const rows = [
    ...village.houses.map((h, i) => ({
      s: h, label: i18n.t('ui.house_n', { n: i + 1 }), id: 'up_' + i,
    })),
    ...village.facilities
      .filter((s) => s.type !== 'construction' && s.type !== 'quest')
      .map((s) => ({ s, label: i18n.t('bld.' + s.type), id: 'upf_' + s.type })),
  ];

  const perPage = 3;
  const pages = Math.max(1, Math.ceil(rows.length / perPage));
  state.upgradePage = Math.max(0, Math.min(state.upgradePage || 0, pages - 1));
  const slice = rows.slice(state.upgradePage * perPage, state.upgradePage * perPage + perPage);

  slice.forEach((row, i) => {
    const y = P.y + 76 + i * 62;
    const { s } = row;
    ui.parchment(P.x + 10, y, P.w - 20, 54);
    ui.text(P.x + 22, y + 15, `${row.label} • ${i18n.t('ui.level', { n: s.level })}`,
      { size: 11, bold: true, color: '#4a3018' });

    const cap = village.maxUpgradeLevel(s.type);
    const hardMax = s.level >= (BUILDINGS[s.type]?.maxLevel ?? 3);
    const gated = !hardMax && s.level >= cap;   // travado pelo nível da vila
    const cost = village.upgradeCost(s);

    let info;
    if (hardMax) info = i18n.t('ui.max');
    else if (gated) info = i18n.t('ui.locked_village', { n: s.level + 1 });
    else info = village.costText(cost, (k) => i18n.t(k));
    ui.text(P.x + 22, y + 36, info, { size: 9, color: gated ? '#8c2f1f' : '#6e4626' });

    ui.button(row.id, P.x + P.w - 100, y + 12, 78, 28,
      hardMax ? i18n.t('ui.max') : i18n.t('ui.upgrade_house'),
      !hardMax && !gated && village.canAfford(cost));
  });

  if (pages > 1) {
    const py = P.y + P.h - 16;
    if (state.upgradePage > 0) ui.button('upage_prev', P.x + 210, py - 8, 36, 18, '‹', true);
    ui.text(P.x + 264, py, `${state.upgradePage + 1}/${pages}`,
      { align: 'center', size: 9, bold: true, color: '#ffe9b8' });
    if (state.upgradePage < pages - 1) ui.button('upage_next', P.x + 282, py - 8, 36, 18, '›', true);
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

// ---------- Tela: Painel de Missões (etapa 1.7) ----------
function drawQuestScreen() {
  ui.rusticPanel(8, 40, 624, 286);
  ui.woodSign(16, 46, 300, 22, i18n.t('ui.quests_title'), 11);
  ui.text(330, 57, i18n.t('ui.quests_sub', { n: quests.completed }),
    { size: 9, color: '#ffe9b8' });
  ui.closeX('back_world', 604, 46);

  const slots = quests.slots;
  for (let i = 0; i < slots; i++) {
    const y = 78 + i * 74;
    const q = quests.list[i];
    ui.parchment(16, y, 608, 66);

    // slot vazio: mostra quanto falta para chegar missão nova
    if (!q) {
      const p = quests.pending[i - quests.list.length];
      const left = p ? Math.ceil(p.left) : quests.renewTime;
      ui.text(320, y + 33, i18n.t('ui.quest_renew', { s: left }),
        { align: 'center', size: 10, color: '#8a6b4a' });
      continue;
    }

    // ícone do que a missão pede
    const spr = q.kind === 'meal' ? cooking.byId(q.key)?.sprite : 'res_' + q.key;
    ui.glow(52, y + 33, 26);
    ctx.drawImage(getSprite(spr || 'res_wood'), 34, y + 15, 36, 36);

    const have = q.have(village);
    const ok = have >= q.qty;
    const name = q.kind === 'meal' ? i18n.t('meal.' + q.key) : i18n.t('res.' + q.key);

    ui.text(86, y + 20, i18n.t('ui.quest_ask', { n: q.qty, name }),
      { size: 12, bold: true, color: '#3c2712' });
    ui.text(86, y + 38, `${have}/${q.qty}`,
      { size: 10, bold: true, color: ok ? '#2f6b3c' : '#8c2f1f' });
    ui.bar(86, y + 46, 150, 7, have / q.qty, ok ? '#4fa562' : '#c9a24a');

    // recompensa
    ui.text(300, y + 22, i18n.t('ui.quest_reward'), { size: 8, color: '#6e4626' });
    ctx.drawImage(getSprite('res_gold'), 300, y + 30, 13, 13);
    ui.text(318, y + 37, String(q.gold), { size: 11, bold: true, color: '#4a3018' });
    ui.text(360, y + 37, `+${q.xp} ${i18n.t('ui.village_xp')}`,
      { size: 10, bold: true, color: '#6b4ea8' });

    ui.button('qdo_' + q.id, 506, y + 18, 100, 30, i18n.t('ui.quest_deliver'), ok, ok);
  }
}

// ---------- Tela: Cozinha (etapa 1.4) ----------
function drawKitchenScreen() {
  ui.rusticPanel(8, 40, 624, 286);
  const lv = village.levelOf('cozinha');
  ui.woodSign(16, 46, 260, 22, `${i18n.t('bld.cozinha')} • ${i18n.t('ui.level', { n: lv })}`, 11);
  ui.closeX('back_world', 604, 46);

  // ----- receitas -----
  ui.text(20, 84, i18n.t('ui.recipes'), { size: 10, bold: true, color: '#ffe9b8' });
  cooking.RECIPES.forEach((r, i) => {
    const x = 16 + i * 116, y = 92, w = 108, h = 128;
    ui.parchment(x, y, w, h);
    const cx = x + w / 2;
    const locked = r.reqKitchen > lv;

    ui.woodSign(x + 4, y + 3, w - 8, 14, i18n.t('meal.' + r.id), 8);
    if (locked) {
      ctx.fillStyle = 'rgba(30,20,10,0.55)';
      ctx.fillRect(x + 1, y + 18, w - 2, h - 19);
      ui.text(cx, y + 60, '?', { align: 'center', size: 18, bold: true, color: '#8a6b4a' });
      ui.text(cx, y + h - 10, i18n.t('ui.needs_kitchen', { n: r.reqKitchen }),
        { align: 'center', size: 8, bold: true, color: '#ffb8a8' });
      return;
    }

    ui.glow(cx, y + 48, 26);
    ctx.drawImage(getSprite(r.sprite), cx - 18, y + 30, 36, 36);
    ui.text(cx, y + 74, `+${r.heal} HP`,
      { align: 'center', size: 10, bold: true, color: '#2f6b3c' });
    ui.text(x + 6, y + 88, `${i18n.t('ui.have')}: ${village.meals[r.id] || 0}`,
      { size: 8, bold: true, color: '#6e4626' });
    drawCostRow(r.cost, x + w - 6, y + 88);
    ui.button('cook_' + r.id, x + 8, y + 96, w - 16, 24, i18n.t('ui.cook'),
      village.canAfford(r.cost), village.canAfford(r.cost));
  });

  // ----- alimentar goblins -----
  ui.text(20, 238, i18n.t('ui.feed_hint'), { size: 9, color: '#ffe9b8' });

  // pratos guardados (escolher qual usar)
  let px0 = 16;
  for (const r of cooking.RECIPES) {
    const n = village.meals[r.id] || 0;
    if (n <= 0) continue;
    const sel = state.feedIdx === r.id;
    ctx.fillStyle = sel ? 'rgba(79,165,98,0.55)' : 'rgba(0,0,0,0.35)';
    ctx.fillRect(px0, 246, 46, 30);
    ctx.strokeStyle = sel ? '#4fa562' : 'rgba(255,233,168,0.4)';
    ctx.lineWidth = sel ? 2 : 1;
    ctx.strokeRect(px0 + 0.5, 246.5, 45, 29);
    ctx.drawImage(getSprite(r.sprite), px0 + 3, 250, 22, 22);
    ui.text(px0 + 40, 262, `x${n}`, { align: 'right', size: 9, bold: true, color: '#ffe9a8' });
    ui.region('pick_' + r.id, px0, 246, 46, 30);
    px0 += 52;
  }
  if (px0 === 16) {
    ui.text(16, 262, i18n.t('ui.no_meals'), { size: 9, color: '#8a8798' });
  }

  // goblins feridos, para curar
  const hurt = village.goblins
    .map((g, i) => ({ g, i }))
    .filter(({ g }) => g.hp < g.maxHp)
    .slice(0, 4);

  if (!hurt.length) {
    ui.text(320, 296, i18n.t('ui.all_healthy'), { size: 9, color: '#8a8798' });
  } else {
    hurt.forEach(({ g, i }, k) => {
      const x = 300 + k * 84;
      ui.parchment(x, 244, 78, 62);
      ctx.drawImage(getSprite('goblin_idle_0'), x + 24, 246, 30, 30);
      ui.text(x + 39, 284, g.name, { align: 'center', size: 8, bold: true, color: '#3c2712' });
      ui.bar(x + 8, 290, 62, 6, g.hp / g.maxHp, '#4fa562');
      ui.text(x + 39, 302, `${g.hp}/${g.maxHp}`, { align: 'center', size: 7, color: '#6e4626' });
      ui.region('feed_' + i, x, 244, 78, 62);
    });
  }
}

// ---------- Tela: Mercado (etapa 1.6) ----------
const MARKET_PER_PAGE = 4;

function drawMarketScreen() {
  ui.rusticPanel(8, 40, 624, 286);
  const lv = market.level(village);
  ui.woodSign(16, 46, 240, 22, i18n.t('ui.market_title'), 11);
  ui.text(268, 57, i18n.t('ui.market_sub', { n: lv, gold: village.res.gold }),
    { size: 9, color: '#ffe9b8' });
  ui.closeX('back_world', 604, 46);

  // mercado ainda não construído (só acontece por save antigo/atalho)
  if (lv <= 0) {
    ui.text(320, 180, i18n.t('ui.market_locked'),
      { align: 'center', size: 12, bold: true, color: '#ffb8a8' });
    return;
  }

  const selling = state.marketTab === 0;
  ui.tab('mtab_0', 22, 74, 110, 20, i18n.t('ui.tab_sell'), selling);
  ui.tab('mtab_1', 140, 74, 110, 20, i18n.t('ui.tab_buy'), !selling);

  // Na venda só faz sentido mostrar o que o jogador realmente tem.
  let items = market.catalog(village, selling ? 'sell' : 'buy');
  if (selling) items = items.filter((it) => it.have > 0);

  if (!items.length) {
    ui.text(320, 200, i18n.t('ui.market_empty'),
      { align: 'center', size: 11, color: '#e8d5a8' });
    return;
  }

  const pages = Math.max(1, Math.ceil(items.length / MARKET_PER_PAGE));
  state.marketPage = Math.max(0, Math.min(state.marketPage, pages - 1));
  const from = state.marketPage * MARKET_PER_PAGE;
  const slice = items.slice(from, from + MARKET_PER_PAGE);

  slice.forEach((it, i) => {
    const x = 16 + i * 153, y = 102, w = 145, h = 176;
    const slot = `${it.kind}:${it.key}`;
    const name = it.kind === 'meal' ? i18n.t('meal.' + it.key) : i18n.t('res.' + it.key);
    const limit = marketLimit(slot);
    const qty = marketQty(slot);
    const total = qty * it.price;

    ui.parchment(x, y, w, h);
    ui.woodSign(x + 4, y + 3, w - 8, 14, name, 8);

    ui.glow(x + w / 2, y + 44, 28);
    ctx.drawImage(getSprite(it.sprite), x + w / 2 - 18, y + 26, 36, 36);

    // preço unitário + quanto o jogador já tem
    ui.text(x + w / 2, y + 72, i18n.t('ui.market_unit', { n: it.price }),
      { align: 'center', size: 9, bold: true, color: '#4a3018' });
    ui.text(x + w / 2, y + 86, `${i18n.t('ui.have')}: ${it.have}`,
      { align: 'center', size: 8, color: '#6e4626' });

    // seletor de quantidade  −  N  +   (máx)
    ui.button('mq_-_' + slot, x + 8, y + 96, 26, 24, '−', limit > 0 && qty > 1);
    ui.text(x + w / 2, y + 108, i18n.t('ui.market_qty', { n: qty }),
      { align: 'center', size: 11, bold: true, color: '#3c2712' });
    ui.button('mq_+_' + slot, x + w - 34, y + 96, 26, 24, '+', qty < limit);
    ui.button('mmax_' + slot, x + 8, y + 124, w - 16, 18,
      `${i18n.t('ui.market_max')} ${limit}`, limit > 0);

    // total e confirmação
    ctx.drawImage(getSprite('res_gold'), x + 8, y + 148, 12, 12);
    ui.text(x + 24, y + 154, String(total),
      { size: 10, bold: true, color: limit > 0 ? '#4a3018' : '#8c2f1f' });
    ui.button('mdo_' + slot, x + 62, y + 146, w - 70, 24,
      selling ? i18n.t('ui.market_sell') : i18n.t('ui.market_buy'),
      limit > 0, limit > 0);
  });

  if (pages > 1) {
    if (state.marketPage > 0) ui.button('mpage_prev', 250, 292, 36, 18, '‹', true);
    ui.text(320, 301, `${state.marketPage + 1}/${pages}`,
      { align: 'center', size: 9, bold: true, color: '#ffe9b8' });
    if (state.marketPage < pages - 1) ui.button('mpage_next', 354, 292, 36, 18, '›', true);
  }
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
    quests: quests.serialize(),
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

  // o balance só existe depois do loadBalance(): agora as missões
  // podem ler slots/tempo de renovação e preencher o painel.
  quests.configure();
  quests.ensure(village.level);

  // ganchos de screenshot (?demo=...)
  const demo = new URLSearchParams(location.search).get('demo');
  if (demo === 'recruit') openRecruit();
  else if (demo === 'roster') state.screen = 'roster';
  else if (demo === 'build') state.screen = 'build';
  else if (demo === 'quests') state.screen = 'quests';
  else if (demo === 'kitchen') state.screen = 'kitchen';
  else if (demo === 'market') {
    // a prévia precisa do Mercado de pé: destrava e constrói na hora
    if (!village.has('mercado')) {
      village.level = Math.max(village.level, BUILDINGS.mercado.reqLevel);
      village.res.wood += 999; village.res.stone += 999; village.res.gold += 999;
      village.build('mercado');
    }
    openMarket();
  }
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
