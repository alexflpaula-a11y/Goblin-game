// ============================================================
// main.js — Boot + game loop + roteamento de telas
// Etapa 1.1: entidade goblin, habitação, recrutamento 1-de-3
// ============================================================
const { CONFIG } = require('config.js');
const { Input } = require('input.js');
const { loadAssets, getSprite } = require('assetLoader.js');
const { i18n, loadI18n } = require('i18n.js');
const { SAVE_ENABLED, saveGame, loadGame, clearGame, startAutosave } = require('save.js');
const { Camera } = require('camera.js');
const { World, WORLD } = require('world.js');
const { Village, BUILDINGS, BUILD_ORDER } = require('village.js');
const { Nodes } = require('nodes.js');
const { Deities } = require('deities.js');
const { UI } = require('ui.js');
const { loadBalance, BAL } = require('balance.js');
const { Goblin, ATTRS } = require('goblin.js');
const gear = require('gear.js');
const inv = require('inventory.js');
const abilities = require('abilities.js');
const { Quests } = require('quests.js');
const cooking = require('cooking.js');
const market = require('market.js');
// ---------- DOM ----------
const viewport = document.getElementById('viewport');
const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');

const titleEl = document.getElementById('title');
const subtitleEl = document.getElementById('subtitle');
const statusEl = document.getElementById('status');

// Configurações (modal) — por enquanto só idioma
const settingsBtn = document.getElementById('settingsBtn');
const settingsModal = document.getElementById('settingsModal');
const settingsClose = document.getElementById('settingsClose');
const settingsTitleEl = document.getElementById('settingsTitle');
const settingsLangLabelEl = document.getElementById('settingsLangLabel');
const langPtBtn = document.getElementById('langPt');
const langEnBtn = document.getElementById('langEn');

// ---------- Estado ----------
const saved = loadGame() || {};
const state = {
  language: saved.language || 'pt-BR',
  taps: saved.taps || 0,
  // world | build | jobs | recruit | roster | detail | quests | kitchen | market | armazem | equip
  screen: 'world',
  buildTab: 0,            // 0 estruturas | 1 melhorias
  buildScroll: 0,         // rolagem vertical do catálogo de estruturas
  candidates: null,       // 3 goblins p/ recrutamento
  detailIdx: 0,
  feedIdx: null,          // prato escolhido p/ alimentar um goblin
  marketTab: 0,           // 0 vender | 1 comprar
  marketScroll: 0,        // rolagem horizontal da prateleira
  marketQty: {},          // quantidade escolhida por item ("res:wood" → 3)
  upgradeIdx: 0,          // casa sendo melhorada (aba Melhorias)
  upgradeScroll: 0,       // rolagem vertical da aba Melhorias
  rosterScroll: 0,        // rolagem vertical da lista de goblins
  jobsScroll: 0,          // rolagem vertical da Área dos Goblins
  toast: null,            // {msg, until}
  levelUp: null,          // {level, until} — banner de nível da vila
  equipIdx: 0,            // goblin sendo equipado
  equipTab: 0,            // 0 equipamento | 1 alimentos | 2 habilidades
  equipSel: null,         // espaço do boneco selecionado ('capacete', ...)
  equipBack: 'armazem',   // p/ onde o "voltar" da tela de equipar vai
  abSel: 0,               // espaço de habilidade selecionado
  invSel: null,            // item selecionado na grade do armazém
  // null | {mode:'build',type,preview,cursorSeq} |
  //        {mode:'pick'} | {mode:'move',structure,type,preview,cursorSeq}
  placement: null,
};

// ---------- Mundo / vila / câmera / UI ----------
const world = new World(7);
const village = new Village(saved.village);
world.setGoblinCount(village.goblins.length);
const nodes = new Nodes(world, saved.nodes);
nodes.syncFacilities(village);          // posto infinito da Fazenda
const deities = new Deities(world, village, nodes);
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
  deity: !!BUILDINGS[id].deity,
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
};

function handleChop(node, goblin) {
  if (node.depleted) return;
  const def = NODE_YIELD[node.type] || NODE_YIELD.tree;

  let yield_ = 1;
  // Trabalhador rende o dobro de vez em quando
  if (goblin?.specialty === 'worker' && Math.random() < 0.35) yield_ += 1;
  // A Serraria melhora o rendimento de árvores naturais ou divinas.
  if (node.type === 'tree' && village.has('serraria')) {
    if (Math.random() < 0.2 * village.levelOf('serraria')) yield_ += 1;
  }

  const key = def.res;
  const color = def.color;

  village.add(key, yield_);
  world.floats.push({
    x: node.x, y: node.y - 36, ttl: 1.3,
    text: `+${yield_} ${i18n.t('res.' + key)}`,
    color,
  });

  // O posto infinito da Fazenda nunca esgota.
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
  // pode ter subido mais de um nível de uma vez: anuncia TUDO que liberou
  const from = village.level - ups + 1;
  const unlocked = [];
  for (let lv = from; lv <= village.level; lv++) {
    unlocked.push(...village.unlockedAt(lv));
  }
  if (unlocked.length) {
    const names = unlocked.map((id) => i18n.t('bld.' + id)).join(', ');
    toast('toast.unlocked', { names });
  }
}

/** Abre o modo de posicionamento; o custo só é pago no toque no terreno. */
function beginBuildPlacement(type) {
  const why = village.blockedReason(type);
  if (why?.reason === 'level') { toast('toast.village_level', { n: why.need }); return; }
  if (why?.reason === 'count') {
    toast(type === 'house' ? 'toast.no_slots' : 'toast.already_built');
    return;
  }
  if (why?.reason === 'cost') { toast('toast.need'); return; }
  state.placement = {
    mode: 'build', type,
    preview: { x: camera.x, y: camera.y },
    cursorSeq: input.cursorSeq,
  };
  state.screen = 'world';
  toast('toast.place_choose', { name: i18n.t('bld.' + type) });
}

function beginMoveSelection() {
  state.placement = { mode: 'pick', cursorSeq: input.cursorSeq };
  state.screen = 'world';
  toast('toast.move_pick');
}

/** Retorna null para uma posição válida ou a chave do erro. */
function placementReason(x, y, ignore = null) {
  const samples = [[0, -3], [-22, -5], [22, -5], [0, -22]];
  if (samples.some(([dx, dy]) => world.tileAtPx(x + dx, y + dy) !== 3)) {
    return 'toast.place_terrain';
  }
  if (village.structures.some((s) => s !== ignore && Math.hypot(x - s.x, y - s.y) < 72)) {
    return 'toast.place_overlap';
  }
  if (nodes.list.some((n) => !n.depleted && !n.infinite && Math.hypot(x - n.x, y - n.y) < 52)) {
    return 'toast.place_node';
  }
  return null;
}

function finishPlacement(x, y) {
  const p = state.placement;
  if (!p || (p.mode !== 'build' && p.mode !== 'move')) return false;
  const reason = placementReason(x, y, p.structure || null);
  if (reason) { toast(reason); return false; }

  if (p.mode === 'build') {
    const s = village.beginBuildAt(p.type, x, y);
    if (!s) { toast('toast.need'); return false; }
    state.placement = null;
    assignBuilder(s);
    toast('toast.construction_started', {
      name: i18n.t('bld.' + p.type), seconds: s.construction.total,
    });
    return true;
  }

  if (BUILDINGS[p.type]?.deity) deities.deactivate(p.type);
  village.move(p.structure, x, y);
  state.placement = null;
  nodes.syncFacilities(village);
  deities.sync();
  toast('toast.moved', { name: i18n.t('bld.' + p.type) });
  return true;
}

/** Compatibilidade interna: agora construir significa escolher a posição. */
function tryBuild(type) { beginBuildPlacement(type); }

// ---------- Obras com goblins ----------
/** Envia um goblin realmente livre para uma lona de obra, se houver um. */
function assignBuilder(structure) {
  const work = structure?.construction;
  if (!work || work.status !== 'building') return null;
  const current = work.worker == null ? null : world.goblins[work.worker];
  if (current?.job?.construction === structure) return current;
  work.worker = null;
  work.working = false;
  const walker = world.goblins.find((w) => !w.job);
  if (!walker) return null;
  walker.job = { type: 'build-goto', construction: structure };
  work.worker = walker.i;
  return walker;
}

/** Obras têm prioridade sobre tarefas automáticas quando há alguém livre. */
function dispatchBuilders() {
  for (const structure of village.constructionSites) assignBuilder(structure);
}

/** Desconta o cronômetro somente enquanto o construtor está martelando. */
function handleConstructionWork(structure, goblin, dt) {
  const work = structure?.construction;
  if (!work || work.status !== 'building') return;
  // A tabela de duração é fixa: especialidade não altera os 10/20/30… s.
  work.remaining = Math.max(0, work.remaining - dt);
  if (work.remaining <= 0) {
    work.status = 'ready';
    work.worker = null;
    work.working = false;
    world.floats.push({
      x: structure.x, y: structure.y - 46, ttl: 1.5,
      text: '✦ ' + i18n.t('ui.construction_done'), color: '#fff3a8',
    });
  }
}

/** Ativa uma obra pronta ao tocar na lona brilhante. */
function collectConstruction(structure) {
  if (!village.completeConstruction(structure)) return false;
  nodes.syncFacilities(village);
  deities.sync();
  const name = i18n.t('bld.' + structure.type);
  if (structure.type === 'house') {
    world.setGoblinCount(village.goblins.length);
    toast('toast.built');
    openRecruit();
  } else {
    toast('toast.built_x', { name });
  }
  return true;
}

/** Começa uma melhoria com lona e construtor, em vez de aplicá-la na hora. */
function beginUpgradeConstruction(structure) {
  if (!structure) return false;
  if (structure.level >= village.maxUpgradeLevel(structure.type)) {
    toast('toast.village_level', { n: structure.level + 1 });
    return false;
  }
  if (!village.beginUpgrade(structure)) {
    toast('toast.need');
    return false;
  }
  assignBuilder(structure);
  toast('toast.construction_started', {
    name: i18n.t('bld.' + structure.type),
    seconds: structure.construction.total,
  });
  return true;
}

// ---------- Área dos Goblins: tarefas automáticas ----------
const TASKS = ['wood', 'stone', 'food'];

function autoAssignWalker(walker) {
  if (!walker || walker.job) return false;
  const goblin = village.goblins[walker.i];
  const task = goblin?.assignment;
  if (!TASKS.includes(task)) return false;
  const node = nodes.findAvailable(task, walker.x, walker.y);
  if (!node) return false;
  return !!nodes.assign(node, [walker]);
}

function setGoblinAssignment(index, task) {
  const goblin = village.goblins[index];
  const walker = world.goblins[index];
  if (!goblin || !walker) return;
  // Um construtor/adorador não pode ser removido por acidente do painel.
  if (walker.job?.construction || walker.job?.deityType) {
    toast('toast.builder_busy');
    return;
  }
  if (walker.job?.node) walker.job.node.worker = null;
  walker.job = null;
  walker.wait = 0.2;
  goblin.assignment = TASKS.includes(task) ? task : null;
  if (goblin.assignment) autoAssignWalker(walker);
  toast(goblin.assignment ? 'toast.job_assigned' : 'toast.job_cleared', {
    name: goblin.name,
    job: i18n.t('job.' + goblin.assignment),
  });
}

// ---------- Mercado (etapa 1.6) ----------
/** Abre a tela do Mercado — só se ele já estiver construído. */
function openMarket() {
  if (!village.has('mercado')) { toast('toast.market_closed'); return; }
  state.screen = 'market';
  state.marketScroll = 0;
}

// ---------- Armazém / equipamento ----------
/** Abre a tela de equipar um goblin (idx do roster). */
function openEquip(idx, backTo = 'armazem') {
  const n = village.goblins.length;
  if (!n) return;
  state.equipIdx = Math.max(0, Math.min(idx || 0, n - 1));
  state.equipBack = backTo;
  state.equipSel = null;
  state.equipTab = 0;
  state.screen = 'equip';
}

/** Cíclo entre os goblins na tela de equipar. */
function cycleEquip(dir) {
  const n = village.goblins.length;
  if (!n) return;
  state.equipIdx = (state.equipIdx + dir + n) % n;
  state.equipSel = null;
}

/** Destrava e constrói o Armazém na hora (gancho ?demo=). */
function ensureArmazem() {
  if (village.has('armazem')) return;
  village.level = Math.max(village.level, BUILDINGS.armazem.reqLevel);
  village.res.wood += 999; village.res.stone += 999;
  village.build('armazem');
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
  const name = kind === 'meal' ? i18n.t('meal.' + key)
    : kind === 'gear' ? i18n.t('item.' + key)
    : i18n.t('res.' + key);

  if (state.marketTab === 0) {
    const gold = market.sell(village, kind, key, qty);
    if (gold > 0) toast('toast.sold', { n: qty, name, gold });
    else toast('toast.market_nothing');
  } else {
    const cost = market.buy(village, kind, key, qty);
    if (cost > 0) {
      // um toast só (não existe fila): a mensagem de compra já
      // traz item, quantidade e preço
      toast('toast.bought', { n: qty, name, gold: cost });
    } else if (kind === 'gear') {
      // falhou: sem ouro ou sem espaço no Armazém?
      if ((village.res.gold || 0) >= market.buyPrice(village, kind, key)) toast('toast.inv_full');
      else toast('toast.market_gold');
    } else toast('toast.market_gold');
  }
  // depois do negócio a quantidade volta ao mínimo
  delete state.marketQty[slot];
}

function routeTap(id) {
  switch (id) {
    case 'close': state.screen = 'world'; break;
    case 'build_btn': state.screen = 'build'; break;
    case 'jobs_btn': state.screen = 'jobs'; state.jobsScroll = 0; break;
    case 'close_jobs': state.screen = 'world'; break;
    case 'move_btn': beginMoveSelection(); break;
    case 'placement_cancel': state.placement = null; toast('toast.place_cancelled'); break;
    case 'close_build': state.screen = 'world'; break;
    case 'tab_0': state.buildTab = 0; state.buildScroll = 0; break;
    case 'tab_1': state.buildTab = 1; state.upgradeScroll = 0; break;
    case 'roster_btn': state.screen = 'roster'; state.rosterScroll = 0; break;
    case 'back_roster': state.screen = 'roster'; break;
    case 'back_world': state.screen = 'world'; state.feedIdx = null; break;
    case 'quests_btn': state.screen = 'quests'; break;
    case 'kitchen_btn': state.screen = 'kitchen'; break;
    case 'market_btn': openMarket(); break;
    case 'armazem_btn': state.screen = 'armazem'; break;
    case 'back_armazem': state.screen = 'world'; break;
    case 'inv_upgrade': {
      const s = village.get('armazem');
      if (s) beginUpgradeConstruction(s);
      break;
    }
    case 'inv_equip': openEquip(0, 'armazem'); break;
    case 'eq_prev': cycleEquip(-1); break;
    case 'eq_next': cycleEquip(1); break;
    case 'eqtab_0': state.equipTab = 0; break;
    case 'eqtab_1': state.equipTab = 1; break;
    case 'eqtab_2': state.equipTab = 2; break;
    case 'back_eq':
      state.screen = state.equipBack === 'detail' ? 'detail' : 'armazem';
      break;
    case 'open_equip': openEquip(state.detailIdx, 'detail'); break;
    case 'mtab_0': state.marketTab = 0; state.marketScroll = 0; break;
    case 'mtab_1': state.marketTab = 1; state.marketScroll = 0; break;
    case 'build_house': tryBuild('house'); break;
    case 'upgrade_house':
      beginUpgradeConstruction(village.houses[state.upgradeIdx || 0]);
      break;
    default:
      // ----- catálogo de construção -----
      if (id?.startsWith('bcard_')) {
        tryBuild(id.slice(6));
        break;
      }
      // ----- melhorar estrutura (aba Melhorias) -----
      if (id?.startsWith('upf_')) {
        beginUpgradeConstruction(village.get(id.slice(4)));
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
      // ----- Área dos Goblins: job_<índice>_<tarefa> -----
      if (id?.startsWith('job_')) {
        const [, idx, task] = id.split('_');
        setGoblinAssignment(Number(idx), task === 'idle' ? null : task);
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
      // ----- armazém: selecionar item da grade -----
      if (id?.startsWith('invs_')) {          // invs_<itemId>
        state.invSel = state.invSel === id.slice(5) ? null : id.slice(5);
        break;
      }
      // ----- equipar: selecionar espaço do boneco -----
      if (id?.startsWith('slot_')) {          // slot_<slotKey>
        const key = id.slice(5);
        state.equipSel = state.equipSel === key ? null : key;
        break;
      }
      // ----- equipar: colocar item do armazém no espaço -----
      if (id?.startsWith('eqdo_')) {          // eqdo_<slotKey>_<itemId>
        const [slotKey, itemId] = id.slice(5).split('_:_');
        const g = village.goblins[state.equipIdx];
        const item = inv.byId(itemId);
        if (g && inv.equip(village, g, slotKey, itemId)) {
          toast('toast.equipped', { name: g.name, item: i18n.t('item.' + itemId) });
        } else if (item && (village.items[itemId] || 0) <= 0) {
          toast('toast.item_gone');
        } else toast('toast.need');
        break;
      }
      // ----- equipar: tirar item do espaço -----
      if (id?.startsWith('equn_')) {          // equn_<slotKey>
        const slotKey = id.slice(5);
        const g = village.goblins[state.equipIdx];
        const out = g && inv.unequip(village, g, slotKey);
        if (out) toast('toast.unequipped', { item: i18n.t('item.' + out) });
        break;
      }
      // ----- habilidades: selecionar espaço / equipar / remover -----
      if (id?.startsWith('abslot_')) {        // abslot_<i>
        state.abSel = Number(id.slice(7));
        break;
      }
      if (id?.startsWith('abeq_')) {          // abeq_<abilityId>
        const abId = id.slice(5);
        const g = village.goblins[state.equipIdx];
        const ab = abilities.byId(abId);
        if (!g || !ab) break;
        if (abilities.hasAbility(g, abId)) {
          abilities.unequipAbility(g, g.skills.indexOf(abId));
          toast('toast.ability_removed', { name: g.name, ab: i18n.t('ab.' + abId) });
        } else if (abilities.equipAbility(g, state.abSel, abId)) {
          toast('toast.ability_equip', { name: g.name, ab: i18n.t('ab.' + abId) });
        } else toast('toast.ability_locked', { spec: i18n.t('spec.' + ab.spec) });
        break;
      }
      if (id?.startsWith('abun_')) {          // abun_<i>
        const g = village.goblins[state.equipIdx];
        const cur = g && abilities.unequipAbility(g, Number(id.slice(5)));
        if (cur) toast('toast.ability_removed', { name: g.name, ab: i18n.t('ab.' + cur) });
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
function updateStatus() {
  statusEl.textContent =
    `${i18n.t('demo.status', { n: state.taps })}  •  ${i18n.t(SAVE_ENABLED ? 'demo.autosave' : 'demo.nosave')}  •  ${i18n.t('stage')}`;
}

function update(dt) {
  const g = input.consume();
  if (g.tap) { state.taps += 1; updateStatus(); }

  // No desktop o fantasma acompanha o mouse; no celular acompanha o dedo.
  if (state.placement && state.placement.mode !== 'pick'
      && input.cursor && input.cursorSeq > (state.placement.cursorSeq ?? -1)) {
    state.placement.preview = camera.screenToWorld(input.cursor.x, input.cursor.y);
    state.placement.cursorSeq = input.cursorSeq;
  }

  if (state.screen === 'world') {
    if (g.pan) camera.panByScreen(g.pan.dx, g.pan.dy);
    if (g.pinch) camera.zoomAt(g.pinch.mx, g.pinch.my, g.pinch.factor);
    if (g.wheel) camera.zoomAt(g.wheel.x, g.wheel.y, g.wheel.factor);
    if (g.tap) {
      const uiHit = ui.hit(g.tap);
      if (uiHit) { routeTap(uiHit); return; }
      const w = camera.screenToWorld(g.tap.x, g.tap.y);

      // Construção/mudança de lugar sempre tem prioridade sobre interações.
      if (state.placement) {
        if (state.placement.mode === 'pick') {
          const picked = village.hitTest(w.x, w.y);
          if (!picked) { toast('toast.move_pick'); return; }
          if (picked.construction) { toast('toast.construction_busy'); return; }
          state.placement = {
            mode: 'move', type: picked.type, structure: picked,
            preview: { x: picked.x, y: picked.y }, cursorSeq: input.cursorSeq,
          };
          toast('toast.move_choose', { name: i18n.t('bld.' + picked.type) });
          return;
        }
        finishPlacement(w.x, w.y);
        return;
      }

      // tocar em goblin trabalhando/louvando → chamar de volta
      for (const wk of world.goblins) {
        if (wk.job && Math.abs(w.x - wk.x) < 12 && Math.abs(w.y - (wk.y - 14)) < 20) {
          if (wk.job.construction) {
            toast('toast.builder_busy');
          } else if (wk.job.deityType) {
            deities.releaseByWalker(wk);
            toast('toast.deity_stopped');
          } else {
            if (wk.job.node) wk.job.node.worker = null;
            // Um toque no trabalhador também interrompe a ordem automática;
            // caso contrário ele voltaria à árvore no frame seguinte.
            const goblin = village.goblins[wk.i];
            if (goblin) goblin.assignment = null;
            wk.job = null;
            wk.wait = 0.3;
            toast('toast.recalled');
          }
          return;
        }
      }
      // Estruturas têm prioridade sobre recursos que estejam atrás delas.
      const s = village.hitTest(w.x, w.y);
      if (s) {
        if (s.construction?.status === 'ready') {
          collectConstruction(s);
        } else if (s.construction) {
          toast('toast.construction_busy');
        } else if (s.type === 'construction') state.screen = 'build';
        else if (s.type === 'house') state.screen = 'roster';
        else if (s.type === 'quest') state.screen = 'quests';
        else if (s.type === 'cozinha') state.screen = 'kitchen';
        else if (s.type === 'mercado') openMarket();
        else if (s.type === 'armazem') state.screen = 'armazem';
        else if (BUILDINGS[s.type]?.deity) {
          if (deities.isActive(s.type)) {
            deities.deactivate(s.type);
            toast('toast.deity_stopped');
          } else {
            const result = deities.activate(s.type, world.goblins);
            if (!result.ok) toast(result.reason === 'no_idle' ? 'toast.no_idle' : 'toast.soon');
            else {
              const name = village.goblins[result.walker.i]?.name || i18n.t('ui.goblin');
              toast('toast.deity_activating', { name, deity: i18n.t('bld.' + s.type) });
            }
          }
        } else toast('toast.soon');
        return;
      }
      const node = nodes.hitTest(w.x, w.y);
      if (node) {
        if (node.worker != null) toast('toast.node_busy');
        else if (!nodes.assign(node, world.goblins)) toast('toast.no_idle');
        return;
      }
    }
  } else {
    // Telas de UI (não-mundo): arrastar ROLA o conteúdo (não pagina).
    if (g.pan) {
      if (state.screen === 'build') {
        if (state.buildTab === 0) state.buildScroll -= g.pan.dy;
        else state.upgradeScroll -= g.pan.dy;
      } else if (state.screen === 'roster') {
        state.rosterScroll -= g.pan.dy;
      } else if (state.screen === 'jobs') {
        state.jobsScroll -= g.pan.dy;
      } else if (state.screen === 'market') {
        state.marketScroll -= g.pan.dx;   // prateleira rola para o lado
      }
      // os limites (min/max) são reajustados no draw de cada tela
    }
    if (g.tap) {
      const uiHit = ui.hit(g.tap);
      if (uiHit) routeTap(uiHit);
      else if (state.screen === 'build') {
        const P = BUILD_PANEL;
        if (g.tap.x < P.x || g.tap.x > P.x + P.w || g.tap.y < P.y || g.tap.y > P.y + P.h) {
          state.screen = 'world';
        }
      }
    }
  }

  // Missões e milagres continuam acontecendo com o tempo. Obras recebem
  // primeiro qualquer goblin livre; depois os demais retomam suas tarefas.
  quests.update(dt, village.level);
  nodes.update(dt);
  deities.update(dt);
  dispatchBuilders();

  world.update(dt, {
    village,
    onChop: handleChop,
    onBuild: handleConstructionWork,
    onAutoTask: autoAssignWalker,
    workPeriod: BAL.nodes?.workPeriod ?? 1.2,
  });
}

function placementDrawList() {
  const p = state.placement;
  if (!p || p.mode === 'pick' || !p.preview) return [];
  const { x, y } = p.preview;
  const valid = !placementReason(x, y, p.structure || null);
  const sprite = BUILDINGS[p.type]?.sprite || 'building_house_1';
  return [{
    y,
    draw: (c) => {
      c.save();
      c.globalAlpha = 0.68;
      c.drawImage(getSprite(sprite), x - 32, y - 60, 64, 64);
      c.globalAlpha = 0.9;
      c.strokeStyle = valid ? '#75e083' : '#ff6b5e';
      c.lineWidth = 2;
      c.beginPath();
      c.ellipse(x, y + 1, 34, 12, 0, 0, Math.PI * 2);
      c.stroke();
      c.fillStyle = valid ? '#9ff0a9' : '#ff9a90';
      c.font = 'bold 10px monospace';
      c.textAlign = 'center';
      c.fillText(valid ? '✓' : '✕', x, y - 66);
      c.restore();
    },
  }];
}

// ---------- Render ----------
function render(time) {
  ctx.imageSmoothingEnabled = false;
  ctx.setTransform(scaleFactor, 0, 0, scaleFactor, 0, 0);
  ctx.fillStyle = '#0d2b47';
  ctx.fillRect(0, 0, CONFIG.LOGICAL_WIDTH, CONFIG.LOGICAL_HEIGHT);

  camera.applyTransform(ctx, scaleFactor);
  world.draw(ctx, time, camera.visible(), [
    ...village.drawList(time), ...nodes.drawList(), ...deities.drawList(time),
    ...placementDrawList(),
  ]);

  ctx.setTransform(scaleFactor, 0, 0, scaleFactor, 0, 0);
  drawOverlay(time);

  ui.begin();
  if (state.screen === 'build') drawBuildScreen();
  else if (state.screen === 'jobs') drawJobsScreen();
  else if (state.screen === 'recruit') drawRecruitScreen();
  else if (state.screen === 'roster') drawRosterScreen();
  else if (state.screen === 'detail') drawDetailScreen();
  else if (state.screen === 'quests') drawQuestScreen();
  else if (state.screen === 'kitchen') drawKitchenScreen();
  else if (state.screen === 'market') drawMarketScreen();
  else if (state.screen === 'armazem') drawArmazemScreen();
  else if (state.screen === 'equip') drawEquipScreen();
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
  if (state.placement) {
    const p = state.placement;
    const key = p.mode === 'pick' ? 'ui.move_pick' : (p.mode === 'move' ? 'ui.move_choose' : 'ui.place_choose');
    const params = p.type ? { name: i18n.t('bld.' + p.type) } : {};
    ui.woodSign(118, 302, 390, 24, i18n.t(key, params), 10);
    ui.button('placement_cancel', 516, 302, 112, 28, i18n.t('ui.cancel'), true);
    return;
  }

  // Barra de ações do mundo — ícones de telas + opção universal de mover.
  const ready = quests.list.filter((q) => q.canDeliver(village)).length;

  const acts = [
    { id: 'build_btn', icon: 'ui_icon_build' },
    { id: 'quests_btn', icon: 'ui_icon_quests',
      badge: ready > 0 ? { text: String(ready), color: '#4fa562', ink: '#0f2a16' } : null },
  ];
  if (village.has('cozinha')) acts.push({ id: 'kitchen_btn', icon: 'ui_icon_kitchen' });
  if (village.has('mercado')) acts.push({ id: 'market_btn', icon: 'ui_icon_market' });
  if (village.has('armazem')) acts.push({ id: 'armazem_btn', icon: 'ui_icon_armazem' });
  acts.push({ id: 'move_btn', glyph: '↔' });
  acts.push({ id: 'jobs_btn', glyph: '⚒' });
  acts.push({
    id: 'roster_btn', icon: 'ui_icon_village', active: true,
    badge: { text: String(village.goblins.length), color: '#a78bfa', ink: '#1b1530' },
  });

  const s = 44, gap = 8, y = 308, iconSize = 34;
  let x = 8;
  for (const a of acts) {
    ui.iconBtn(a.id, x, y, s, !!a.active);
    if (a.icon) {
      ctx.drawImage(getSprite(a.icon), x + (s - iconSize) / 2, y + (s - iconSize) / 2, iconSize, iconSize);
    } else {
      ui.text(x + s / 2, y + s / 2 + 2, a.glyph || '?', {
        align: 'center', size: 23, bold: true, color: '#ffe9a8',
      });
    }
    if (a.badge) ui.badge(x + s - 6, y + 6, a.badge.text, a.badge.color, a.badge.ink);
    x += s + gap;
  }
}

// ---------- Tela: Casa de Construção (painel rústico c/ abas) ----------
function drawBuildScreen() {
  const P = BUILD_PANEL;
  ui.rusticPanel(P.x, P.y, P.w, P.h);
  ui.woodSign(P.x + 8, P.y + 6, P.w - 46, 22, i18n.t('ui.build_title'), 12);
  ui.closeX('close_build', P.x + P.w - 36, P.y + 6);

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
  // O catálogo mostra TODAS as estruturas em 3 colunas; arrasta p/ CIMA/BAIXO.
  const cols = 3, w = 164, h = 118, rowH = 122;
  const rows = Math.ceil(BUILD_DEFS.length / cols);
  const viewTop = P.y + 60, viewBot = P.y + P.h - 10, viewH = viewBot - viewTop;
  const contentH = rows * rowH;
  const maxScroll = Math.max(0, contentH - viewH);
  state.buildScroll = Math.max(0, Math.min(state.buildScroll, maxScroll));

  const c = ctx;
  c.save();
  c.beginPath();
  c.rect(P.x, viewTop, P.w, viewH);
  c.clip();

  BUILD_DEFS.forEach((def, i) => {
    const col = i % cols, row = Math.floor(i / cols);
    const x = P.x + 10 + col * 172;
    const y = viewTop + row * rowH - state.buildScroll;
    // culling: fora da janela visível → não desenha nem registra clique
    if (y + h < viewTop - 2 || y > viewBot + 2) return;
    ui.parchment(x, y, w, h);

    ui.woodSign(x + 4, y + 3, w - 8, 14, i18n.t('bld.' + def.id), 8);
    const cx = x + w / 2;
    if (def.deity) {
      ui.text(cx, y + 27, i18n.t('ui.deity'), {
        align: 'center', size: 7, bold: true, color: '#9b5f16',
      });
    }
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
      ui.text(cx, y + 94, i18n.t('ui.build_time', { s: village.constructionSeconds(def.id, 1) }),
        { align: 'center', size: 7, bold: true, color: '#6e4626' });
      if (maxCount > 1) {
        ui.text(x + 6, y + h - 9, i18n.t('ui.built_count', { n: built, max: maxCount }),
          { size: 8, bold: true, color: '#6e4626' });
      }
      drawCostRow(village.buildCost(def.id), x + w - 8, y + h - 9);
      ui.region('bcard_' + def.id, x, y, w, h);
    }
  });

  c.restore();
  // barra de rolagem vertical
  ui.scrollbarV(P.x + P.w - 8, viewTop, viewH, state.buildScroll, maxScroll, viewH, contentH);
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

  // Lista rolável (arrasta p/ CIMA/BAIXO).
  const rowH = 62;
  const viewTop = P.y + 74, viewBot = P.y + P.h - 10, viewH = viewBot - viewTop;
  const contentH = rows.length * rowH;
  const maxScroll = Math.max(0, contentH - viewH);
  state.upgradeScroll = Math.max(0, Math.min(state.upgradeScroll || 0, maxScroll));

  const c = ctx;
  c.save();
  c.beginPath();
  c.rect(P.x, viewTop, P.w, viewH);
  c.clip();

  rows.forEach((row, i) => {
    const y = viewTop + 2 + i * rowH - state.upgradeScroll;
    if (y + 54 < viewTop - 2 || y > viewBot + 2) return;
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

  c.restore();
  ui.scrollbarV(P.x + P.w - 8, viewTop, viewH, state.upgradeScroll, maxScroll, viewH, contentH);
}

// ---------- Tela: Área dos Goblins (tarefas automáticas) ----------
function drawJobsScreen() {
  const P = { x: 16, y: 30, w: 608, h: 300 };
  ui.rusticPanel(P.x, P.y, P.w, P.h);
  ui.woodSign(P.x + 8, P.y + 6, 244, 22, i18n.t('ui.jobs_title'), 12);
  ui.closeX('close_jobs', P.x + P.w - 38, P.y + 6);
  ui.text(P.x + 16, P.y + 64, i18n.t('ui.jobs_sub'), { size: 9, color: '#ffe9b8' });

  const rowH = 64;
  const viewTop = P.y + 76, viewBot = P.y + P.h - 10, viewH = viewBot - viewTop;
  const contentH = village.goblins.length * rowH;
  const maxScroll = Math.max(0, contentH - viewH);
  state.jobsScroll = Math.max(0, Math.min(state.jobsScroll || 0, maxScroll));

  ctx.save();
  ctx.beginPath();
  ctx.rect(P.x + 4, viewTop, P.w - 12, viewH);
  ctx.clip();
  village.goblins.forEach((goblin, i) => {
    const y = viewTop + i * rowH - state.jobsScroll;
    if (y + rowH < viewTop || y > viewBot) return;
    const walker = world.goblins[i];
    const isBuilder = !!walker?.job?.construction;
    const isWorshipper = !!walker?.job?.deityType;
    const task = goblin.assignment;
    const status = isBuilder ? i18n.t('ui.job_building')
      : isWorshipper ? i18n.t('ui.job_worshipping')
        : task ? i18n.t('ui.job_auto', { job: i18n.t('job.' + task) })
          : i18n.t('ui.job_idle');

    ui.parchment(P.x + 8, y + 2, P.w - 22, 58);
    ctx.drawImage(getSprite(gear.spriteForGoblin(goblin, 'idle', i % 5)), P.x + 13, y + 10, 40, 40);
    ui.text(P.x + 59, y + 21, goblin.name, { size: 10, bold: true, color: '#3c2712' });
    ui.text(P.x + 59, y + 38, status, {
      size: 8, color: isBuilder ? '#8c2f1f' : '#6e4626',
    });

    const bx = P.x + 248, by = y + 17, bw = 70, bh = 26;
    const locked = isBuilder || isWorshipper;
    ui.button('job_' + i + '_idle', bx, by, bw, bh, i18n.t('job.idle'), !locked && !!task);
    ui.button('job_' + i + '_wood', bx + 76, by, bw, bh, i18n.t('job.wood'), !locked && task !== 'wood');
    ui.button('job_' + i + '_stone', bx + 152, by, bw, bh, i18n.t('job.stone'), !locked && task !== 'stone');
    ui.button('job_' + i + '_food', bx + 228, by, bw, bh, i18n.t('job.food'), !locked && task !== 'food');
  });
  ctx.restore();
  ui.scrollbarV(P.x + P.w - 8, viewTop, viewH, state.jobsScroll, maxScroll, viewH, contentH);
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
    ctx.drawImage(getSprite(gear.spriteForGoblin(g, 'idle', i % 5)), cx - 28, y + 16, 56, 56);

    ui.text(cx, y + 84, g.name, { align: 'center', size: 12, bold: true, color: '#3c2712' });
    ui.text(cx, y + 100, `${i18n.t('spec.' + g.specialty)} • ${i18n.t('rarity.' + g.rarity)} ${'★'.repeat(RARITIES_IDX(g.rarity) + 1)}`,
      { align: 'center', size: 9, color: '#6e4626' });
    if (g.variation) {
      ui.text(cx, y + 114, i18n.t('variation.' + g.variation),
        { align: 'center', size: 8, bold: true, color: '#8c4f32' });
    }

    ATTRS.forEach((a, ai) => {
      const col = ai % 2, row = Math.floor(ai / 2);
      const bx = x + 12 + col * 100, by = y + 132 + row * 24;
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

  // Lista rolável (arrasta p/ CIMA/BAIXO) — mostra TODOS os goblins.
  const rowH = 60;
  const rows = Math.ceil(village.goblins.length / 2);
  const viewTop = 72, viewBot = 292, viewH = viewBot - viewTop;
  const contentH = rows * rowH;
  const maxScroll = Math.max(0, contentH - viewH);
  state.rosterScroll = Math.max(0, Math.min(state.rosterScroll, maxScroll));

  const c = ctx;
  c.save();
  c.beginPath();
  c.rect(8, viewTop, 624, viewH);
  c.clip();

  village.goblins.forEach((g, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 16 + col * 308, y = viewTop + 4 + row * rowH - state.rosterScroll, w = 300, h = 56;
    if (y + h < viewTop - 2 || y > viewBot + 2) return;
    ui.parchment(x, y, w, h);
    ui.region('g_' + i, x, y, w, h);
    ctx.drawImage(getSprite(gear.spriteForGoblin(g, 'idle', 0)), x + 8, y + 10, 36, 36);
    ui.text(x + 52, y + 16, `${g.name}  ${i18n.t('ui.level', { n: g.level })}`, { size: 11, bold: true, color: '#3c2712' });
    ui.text(x + 52, y + 34, `${i18n.t('spec.' + g.specialty)} • ${i18n.t('rarity.' + g.rarity)}`, { size: 9, color: '#6e4626' });
    ui.bar(x + 212, y + 14, 78, 8, g.hp / g.maxHp, '#4fa562');
    ui.text(x + 212, y + 34, `HP ${g.hp}/${g.maxHp}`, { size: 8, color: '#6e4626' });
  });

  c.restore();
  ui.scrollbarV(626, viewTop, viewH, state.rosterScroll, maxScroll, viewH, contentH);
  ui.button('back_world', 272, 298, 96, 24, i18n.t('ui.close'), true, true);
}

// ---------- Tela: Detalhe do goblin ----------
function drawDetailScreen() {
  const g = village.goblins[state.detailIdx];
  if (!g) { state.screen = 'roster'; return; }
  ui.rusticPanel(60, 40, 520, 286);
  ui.woodSign(70, 48, 220, 22, g.name, 12);
  ui.glow(130, 130, 46);
  ctx.drawImage(getSprite(gear.spriteForGoblin(g, 'idle', 0)), 94, 84, 72, 72);
  ui.text(94, 172, i18n.t('spec.' + g.specialty), { size: 11, bold: true, color: '#ffe9b8' });
  ui.text(94, 188, `${i18n.t('rarity.' + g.rarity)} ${'★'.repeat(RARITIES_IDX(g.rarity) + 1)}`, { size: 9, color: '#ffe9b8' });
  if (g.variation) {
    ui.text(94, 204, i18n.t('variation.' + g.variation), { size: 8, bold: true, color: '#d9cdfa' });
  }
  ui.text(94, 220, i18n.t('ui.level', { n: g.level }), { size: 10, color: '#ffe9b8' });
  ui.bar(94, 228, 140, 8, g.xp / g.xpNext(), '#e8b23a');

  ATTRS.forEach((a, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const ax = 250 + col * 165, ay = 84 + row * 36;
    ui.text(ax, ay, i18n.t('attr.' + a), { size: 9, color: '#ffe9b8' });
    ui.bar(ax, ay + 8, 120, 9, g[a] / 10, RARITY_COLOR[g.rarity]);
    ui.text(ax + 128, ay + 4, `${g[a]}/10`, { size: 10, bold: true, color: '#efeafd' });
  });

  ui.text(250, 208, `HP ${g.hp}/${g.maxHp}   MP ${g.mp}/${g.maxMp}`, { size: 10, color: '#b9aedc' });
  ui.text(250, 228, i18n.t('ui.equipped_count', { n: inv.equippedCount(g) }), { size: 9, color: '#b9aedc' });
  ui.button('back_roster', 240, 292, 100, 26, i18n.t('ui.back'), true, true);
  ui.button('open_equip', 352, 292, 120, 26, i18n.t('ui.equip_btn'), true, true);
}

// ---------- Tela: Painel de Missões (etapa 1.7) ----------
function drawQuestScreen() {
  ui.rusticPanel(8, 40, 624, 286);
  ui.woodSign(16, 46, 300, 22, i18n.t('ui.quests_title'), 11);
  ui.text(330, 57, i18n.t('ui.quests_sub', { n: quests.completed }),
    { size: 9, color: '#ffe9b8' });
  ui.closeX('back_world', 598, 44);

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
  ui.closeX('back_world', 598, 44);

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
      ctx.drawImage(getSprite(gear.spriteForGoblin(g, 'idle', 0)), x + 24, 246, 30, 30);
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
  // equipamentos só entram na prateleira com Armazém construído
  if (!village.has('armazem')) {
    ui.text(268, 57, i18n.t('ui.market_need_armazem'), { size: 8, color: '#ffb8a8' });
  } else {
    ui.text(268, 57, i18n.t('ui.market_sub', { n: lv, gold: village.res.gold }),
      { size: 9, color: '#ffe9b8' });
  }
  ui.closeX('back_world', 598, 44);

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

  // Prateleira rolável na HORIZONTAL (arrasta para o lado).
  const w = 145, h = 176, colW = 153;
  const viewLeft = 12, viewRight = 628, viewW = viewRight - viewLeft;
  const contentW = items.length * colW;
  const maxScroll = Math.max(0, contentW - viewW);
  state.marketScroll = Math.max(0, Math.min(state.marketScroll, maxScroll));

  const cc = ctx;
  cc.save();
  cc.beginPath();
  cc.rect(viewLeft, 100, viewW, h + 6);
  cc.clip();

  items.forEach((it, i) => {
    const x = 16 + i * colW - state.marketScroll, y = 102;
    if (x + w < viewLeft - 2 || x > viewRight + 2) return;
    const slot = `${it.kind}:${it.key}`;
    const name = it.kind === 'meal' ? i18n.t('meal.' + it.key)
      : it.kind === 'gear' ? i18n.t('item.' + it.key)
      : i18n.t('res.' + it.key);
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

  cc.restore();
  ui.scrollbarH(viewLeft, 292, viewW, state.marketScroll, maxScroll, viewW, contentW);
}

// ---------- Tela: Armazém / Inventário ----------
/** Grade de espaços de itens: cada célula = 1 item guardado. */
function drawArmazemScreen() {
  ui.rusticPanel(8, 40, 624, 286);
  const lv = village.levelOf('armazem');
  ui.woodSign(16, 46, 236, 22, `${i18n.t('bld.armazem')} • ${i18n.t('ui.level', { n: lv })}`, 11);
  ui.closeX('back_world', 598, 44);

  // ----- área 1: recursos da vila -----
  ui.text(20, 84, i18n.t('ui.res_section'), { size: 10, bold: true, color: '#ffe9b8' });
  const RES_LIST = ['wood', 'stone', 'ore', 'food', 'gold'];
  RES_LIST.forEach((k, i) => {
    const y = 96 + i * 21;
    ctx.drawImage(getSprite('res_' + k), 22, y - 7, 14, 14);
    ui.text(42, y, i18n.t('res.' + k), { size: 10, color: '#e8d5a8' });
    ui.text(240, y, String(village.res[k] || 0), { size: 10, bold: true, align: 'right', color: '#ffe9a8' });
  });

  // ----- despensa (pratos cozinhados) -----
  ui.text(20, 214, i18n.t('ui.pantry'), { size: 10, bold: true, color: '#ffe9b8' });
  let my = 226;
  let mx = 22;
  let pantryShown = 0;
  for (const r of cooking.RECIPES) {
    const n = village.meals[r.id] || 0;
    if (n <= 0) continue;
    pantryShown += 1;
    ctx.fillStyle = 'rgba(0,0,0,0.35)';
    ctx.fillRect(mx, my, 58, 26);
    ctx.strokeStyle = 'rgba(255,233,168,0.4)'; ctx.lineWidth = 1;
    ctx.strokeRect(mx + 0.5, my + 0.5, 57, 25);
    ctx.drawImage(getSprite(r.sprite), mx + 3, my + 3, 20, 20);
    ui.text(mx + 50, my + 13, `x${n}`, { align: 'right', size: 9, bold: true, color: '#ffe9a8' });
    mx += 64;
    if (mx > 200) { mx = 22; my += 30; }
  }
  if (!pantryShown) ui.text(22, 240, i18n.t('ui.no_meals'), { size: 9, color: '#8a8798' });

  // ----- área 2: itens de equipamento (separados em espaços) -----
  ui.text(262, 84, i18n.t('ui.items_section'), { size: 10, bold: true, color: '#ffe9b8' });
  const cap = village.itemCapacity();
  const used = village.itemsCount();
  ui.text(612, 84, i18n.t('ui.items_count', { n: used, max: cap }),
    { size: 10, bold: true, align: 'right', color: used > cap ? '#ff8a8a' : '#ffe9a8' });

  // células: 8 por linha, cada uma com 1 item (ordem do catálogo).
  // Estouro (desequipar com armazém cheio) ganha linhas extras —
  // nada fica invisível; as células tracejadas param no cap.
  const COLS = 8, CELL = 40, GAP = 4;
  const rows = Math.max(Math.ceil(cap / COLS), Math.ceil(used / COLS));
  const cells = [];
  for (const it of inv.ITEMS) {
    const n = village.items[it.id] || 0;
    for (let k = 0; k < n; k++) cells.push(it);
  }
  for (let i = cells.length; i < cap; i++) cells.push(null);

  cells.forEach((it, i) => {
    const col = i % COLS, row = Math.floor(i / COLS);
    const x = 262 + col * (CELL + GAP), y = 94 + row * (CELL + GAP);
    if (it) {
      ui.parchment(x, y, CELL, CELL);
      ctx.drawImage(getSprite(it.icon), x + 6, y + 6, 28, 28);
      const sel = state.invSel === it.id;
      if (sel) {
        ctx.strokeStyle = '#a78bfa'; ctx.lineWidth = 2;
        ctx.strokeRect(x + 1, y + 1, CELL - 2, CELL - 2);
      }
      ui.region('invs_' + it.id, x, y, CELL, CELL);
    } else {
      // espaço vazio: caixa tracejada
      ctx.fillStyle = 'rgba(0,0,0,0.3)';
      ctx.fillRect(x, y, CELL, CELL);
      ctx.strokeStyle = 'rgba(255,233,168,0.22)'; ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      ctx.strokeRect(x + 0.5, y + 0.5, CELL - 1, CELL - 1);
      ctx.setLineDash([]);
    }
  });

  // nota sobre o item selecionado (logo abaixo da grade)
  const noteY = 94 + rows * (CELL + GAP) + 10;
  if (state.invSel && inv.byId(state.invSel)) {
    const it = inv.byId(state.invSel);
    ui.text(262, noteY, `${i18n.t('item.' + it.id)} • ${i18n.t('slot.' + it.slot)}`,
      { size: 9, bold: true, color: '#e8d5a8' });
  } else {
    ui.text(262, noteY, i18n.t('ui.inv_hint'), { size: 9, color: '#8a8798' });
  }

  // ----- rodapé: melhorar o armazém + equipar goblins -----
  const s = village.get('armazem');
  if (!s) { state.screen = 'world'; return; }   // seguro: nunca deveria acontecer
  const hardMax = s.level >= BUILDINGS.armazem.maxLevel;
  const gated = !hardMax && s.level >= village.maxUpgradeLevel('armazem');
  const cost = village.upgradeCost(s);
  let info;
  if (hardMax) info = i18n.t('ui.max');
  else if (gated) info = i18n.t('ui.locked_village', { n: s.level + 1 });
  else info = village.costText(cost, (k) => i18n.t(k));
  ui.button('inv_upgrade', 20, 294, 96, 24, i18n.t('ui.upgrade_house'),
    !hardMax && !gated && village.canAfford(cost));
  ui.text(128, 302, i18n.t('ui.armazem_up_info', { n: cap + (hardMax ? 0 : 8) }),
    { size: 8, color: '#b99b6f' });
  ui.text(128, 314, info, { size: 8, color: gated ? '#8c2f1f' : '#b99b6f' });
  ui.button('inv_equip', 420, 294, 190, 24, i18n.t('ui.equip_goblins'), true, true);
}

// ---------- Tela: Equipar goblin (boneco + abas) ----------
/** Posições dos 10 espaços rodando o personagem (elipse). */
const RING_SLOTS = [
  { key: 'capacete', ang: -90 },
  { key: 'colar', ang: -54 },
  { key: 'arma_primaria', ang: -18 },
  { key: 'anel1', ang: 18 },
  { key: 'botas', ang: 54 },
  { key: 'calca', ang: 90 },
  { key: 'anel2', ang: 126 },
  { key: 'arma_secundaria', ang: 162 },
  { key: 'runa', ang: 198 },
  { key: 'peitoral', ang: 234 },
];

function ringPos(ang) {
  const cx = 250, cy = 208, rx = 96, ry = 92;
  const rad = (ang * Math.PI) / 180;
  return { x: cx + rx * Math.cos(rad), y: cy + ry * Math.sin(rad) };
}

function drawEquipScreen() {
  const g = village.goblins[state.equipIdx];
  if (!g) { state.screen = 'armazem'; return; }
  ui.rusticPanel(8, 40, 624, 286);
  ui.woodSign(16, 46, 150, 22, i18n.t('ui.equip_title'), 11);
  ui.closeX('back_eq', 598, 45);

  // ----- seletor de goblin (‹ nome ›) — setas grandes flanqueando o nome -----
  const n = village.goblins.length;
  const midW = 168, midX = 348;
  ctx.fillStyle = 'rgba(0,0,0,0.35)';
  ctx.fillRect(midX - midW / 2, 47, midW, 22);
  ui.text(midX, 58, `${g.name}  ${i18n.t('ui.level', { n: g.level })} (${state.equipIdx + 1}/${n})`,
    { align: 'center', size: 10, bold: true, color: '#ffe9a8' });
  if (n > 1) {
    ui.arrowBtn('eq_prev', midX - midW / 2 - 36, 44, 30, -1);
    ui.arrowBtn('eq_next', midX + midW / 2 + 6, 44, 30, 1);
  }

  // ----- abas -----
  ui.tab('eqtab_0', 22, 74, 110, 20, i18n.t('ui.tab_equipment'), state.equipTab === 0);
  ui.tab('eqtab_1', 140, 74, 100, 20, i18n.t('ui.tab_food'), state.equipTab === 1);
  ui.tab('eqtab_2', 248, 74, 110, 20, i18n.t('ui.tab_skills'), state.equipTab === 2);

  if (state.equipTab === 0) drawEquipTabGear(g);
  else if (state.equipTab === 1) drawEquipTabFood(g);
  else drawEquipTabSkills(g);
}

/** Aba EQUIPAMENTO: goblin no centro, 10 espaços rodando ele. */
function drawEquipTabGear(g) {
  // goblin no centro (idle animado)
  const frame = Math.floor(performance.now() / 240) % 5;
  ui.glow(250, 208, 62);
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(getSprite(gear.spriteForGoblin(g, 'idle', frame)), 214, 152, 72, 72);
  ui.bar(200, 236, 100, 8, g.hp / g.maxHp, '#4fa562');
  ui.text(250, 252, `HP ${g.hp}/${g.maxHp}`, { align: 'center', size: 8, color: '#e8d5a8' });

  // ----- anel de espaços -----
  const SLOT_BOX = 36;
  for (const { key, ang } of RING_SLOTS) {
    const p = ringPos(ang);
    const x = p.x - SLOT_BOX / 2, y = p.y - SLOT_BOX / 2;
    const item = inv.byId(g.equip?.[key]);
    const sel = state.equipSel === key;

    if (item) {
      ui.parchment(x, y, SLOT_BOX, SLOT_BOX);
      ctx.drawImage(getSprite(item.icon), x + 5, y + 5, 26, 26);
    } else {
      ctx.fillStyle = 'rgba(0,0,0,0.38)';
      ctx.fillRect(x, y, SLOT_BOX, SLOT_BOX);
      ctx.strokeStyle = 'rgba(255,233,168,0.25)'; ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      ctx.strokeRect(x + 0.5, y + 0.5, SLOT_BOX - 1, SLOT_BOX - 1);
      ctx.setLineDash([]);
    }
    if (sel) {
      ctx.strokeStyle = '#a78bfa'; ctx.lineWidth = 2;
      ctx.strokeRect(x + 1, y + 1, SLOT_BOX - 2, SLOT_BOX - 2);
    }
    ui.region('slot_' + key, x, y, SLOT_BOX, SLOT_BOX);
    ui.text(p.x, y + SLOT_BOX + 7, inv.slotName(i18n.t, key),
      { align: 'center', size: 7, color: sel ? '#d9cdfa' : '#b99b6f' });
  }

  // ----- painel da direita: equipar/remover -----
  const px = 402, pw = 214;
  if (!state.equipSel) {
    ui.text(px + pw / 2, 130, i18n.t('ui.equip_hint'),
      { align: 'center', size: 9, color: '#e8d5a8' });
    // resumo do que já está vestido
    ui.text(px + pw / 2, 160, i18n.t('ui.equipped_count', { n: inv.equippedCount(g) }),
      { align: 'center', size: 9, color: '#b99b6f' });
    let yy = 180;
    for (const { key } of RING_SLOTS) {
      const it = inv.byId(g.equip?.[key]);
      if (!it) continue;
      ctx.drawImage(getSprite(it.icon), px + 8, yy - 7, 14, 14);
      ui.text(px + 28, yy, `${i18n.t('item.' + it.id)}`, { size: 8, color: '#e8d5a8' });
      ui.text(px + pw - 8, yy, inv.slotName(i18n.t, key),
        { size: 7, align: 'right', color: '#b99b6f' });
      yy += 17;
    }
    return;
  }

  const slotKey = state.equipSel;
  ui.woodSign(px, 100, pw, 20, inv.slotName(i18n.t, slotKey), 10);

  let yy = 128;
  const cur = inv.byId(g.equip?.[slotKey]);
  if (cur) {
    ui.parchment(px, yy, pw, 48);
    ctx.drawImage(getSprite(cur.icon), px + 8, yy + 8, 32, 32);
    ui.text(px + 48, yy + 18, i18n.t('item.' + cur.id), { size: 10, bold: true, color: '#3c2712' });
    ui.text(px + 48, yy + 33, i18n.t('ui.equipped_now'), { size: 7, color: '#6e4626' });
    ui.button('equn_' + slotKey, px + pw - 74, yy + 12, 66, 22, i18n.t('ui.equip_remove'), true);
    yy += 56;
  } else {
    ui.text(px + pw / 2, yy + 4, i18n.t('ui.equip_none'),
      { align: 'center', size: 9, color: '#b99b6f' });
    yy += 20;
  }

  const options = inv.itemsForSlot(village, slotKey);
  if (!options.length) {
    ui.text(px + pw / 2, yy + 6, i18n.t('ui.none_of_type'),
      { align: 'center', size: 9, color: '#8a8798' });
    return;
  }
  for (const it of options) {
    ui.parchment(px, yy, pw, 46);
    ctx.drawImage(getSprite(it.icon), px + 8, yy + 7, 32, 32);
    ui.text(px + 48, yy + 16, i18n.t('item.' + it.id), { size: 10, bold: true, color: '#3c2712' });
    ui.text(px + 48, yy + 32, `x${it.have}`, { size: 8, color: '#6e4626' });
    ui.button(`eqdo_${slotKey}_:_${it.id}`, px + pw - 74, yy + 11, 66, 22,
      i18n.t('ui.equip_do'), true, true);
    yy += 52;
  }
}

/** Aba ALIMENTOS: escolher prato e alimentar qualquer goblin. */
function drawEquipTabFood() {
  ui.text(20, 112, i18n.t('ui.feed_hint'), { size: 9, color: '#ffe9b8' });

  // pratos guardados
  let px0 = 16;
  for (const r of cooking.RECIPES) {
    const n = village.meals[r.id] || 0;
    if (n <= 0) continue;
    const sel = state.feedIdx === r.id;
    ctx.fillStyle = sel ? 'rgba(79,165,98,0.55)' : 'rgba(0,0,0,0.35)';
    ctx.fillRect(px0, 124, 52, 32);
    ctx.strokeStyle = sel ? '#4fa562' : 'rgba(255,233,168,0.4)';
    ctx.lineWidth = sel ? 2 : 1;
    ctx.strokeRect(px0 + 0.5, 124.5, 51, 31);
    ctx.drawImage(getSprite(r.sprite), px0 + 3, 128, 24, 24);
    ui.text(px0 + 46, 140, `x${n}`, { align: 'right', size: 9, bold: true, color: '#ffe9a8' });
    ui.region('pick_' + r.id, px0, 124, 52, 32);
    px0 += 58;
  }
  if (px0 === 16) ui.text(16, 140, i18n.t('ui.no_meals'), { size: 9, color: '#8a8798' });

  // goblins para alimentar (2 colunas × 3 linhas)
  village.goblins.slice(0, 6).forEach((gg, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 300 + col * 160, y = 104 + row * 72;
    ui.parchment(x, y, 150, 64);
    const sel = state.equipIdx === village.goblins.indexOf(gg);
    if (sel) {
      ctx.strokeStyle = '#a78bfa'; ctx.lineWidth = 2;
      ctx.strokeRect(x + 1, y + 1, 148, 62);
    }
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(getSprite(gear.spriteForGoblin(gg, 'idle', 0)), x + 6, y + 12, 40, 40);
    ui.text(x + 52, y + 16, gg.name, { size: 9, bold: true, color: '#3c2712' });
    ui.bar(x + 52, y + 28, 90, 7, gg.hp / gg.maxHp, '#4fa562');
    ui.text(x + 52, y + 44, `HP ${gg.hp}/${gg.maxHp}`, { size: 8, color: '#6e4626' });
    ui.text(x + 52, y + 56, `+${i18n.t('ui.feed_heal')}`, { size: 7, color: '#2f6b3c' });
    ui.region('feed_' + village.goblins.indexOf(gg), x, y, 150, 64);
  });
  if (village.goblins.length > 6) {
    ui.text(460, 316, `+${village.goblins.length - 6} …`, { size: 9, color: '#ffe9b8' });
  }
}

/** Aba HABILIDADES: 2 espaços + catálogo. */
function drawEquipTabSkills(g) {
  // goblin + especialidade
  ui.glow(70, 130, 40);
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(getSprite(gear.spriteForGoblin(g, 'idle', 0)), 38, 96, 64, 64);
  ui.text(70, 176, g.name, { align: 'center', size: 10, bold: true, color: '#ffe9a8' });
  ui.text(70, 190, i18n.t('spec.' + g.specialty), { align: 'center', size: 8, color: '#b99b6f' });
  ui.text(70, 214, i18n.t('ui.skills_hint'), { align: 'center', size: 7, color: '#b99b6f' });

  // ----- 2 espaços de habilidade -----
  for (let i = 0; i < abilities.SKILL_SLOTS; i++) {
    const x = 26, y = 230 + i * 48;
    const abId = g.skills?.[i];
    const ab = abilities.byId(abId);
    const sel = state.abSel === i;
    if (ab) {
      ui.parchment(x, y, 88, 46);
      ctx.drawImage(getSprite(ab.icon), x + 6, y + 7, 32, 32);
      ui.text(x + 44, y + 18, i18n.t('ab.' + ab.id), { size: 8, bold: true, color: '#3c2712' });
      ui.button('abun_' + i, x + 44, y + 27, 38, 14, '✕', true);
    } else {
      ctx.fillStyle = 'rgba(0,0,0,0.38)';
      ctx.fillRect(x, y, 88, 46);
      ctx.strokeStyle = 'rgba(255,233,168,0.25)'; ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      ctx.strokeRect(x + 0.5, y + 0.5, 87, 45);
      ctx.setLineDash([]);
      ui.text(x + 44, y + 23, `${i18n.t('ui.skill_slot')} ${i + 1}`,
        { align: 'center', size: 8, color: '#8a8798' });
    }
    if (sel) {
      ctx.strokeStyle = '#a78bfa'; ctx.lineWidth = 2;
      ctx.strokeRect(x + 1, y + 1, 86, 44);
    }
    ui.region('abslot_' + i, x, y, 88, 46);
  }

  // ----- catálogo (2 colunas × 5) -----
  abilities.ABILITIES.forEach((ab, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 150 + col * 234, y = 104 + row * 44;
    const can = abilities.canEquip(g, ab);
    const has = abilities.hasAbility(g, ab.id);
    ui.parchment(x, y, 226, 40);
    ctx.globalAlpha = can ? 1 : 0.55;
    ctx.drawImage(getSprite(ab.icon), x + 5, y + 4, 32, 32);
    ui.text(x + 44, y + 13, i18n.t('ab.' + ab.id), { size: 9, bold: true, color: can ? '#3c2712' : '#8a6b4a' });
    ui.text(x + 44, y + 27, i18n.t('abd.' + ab.id), { size: 6, color: '#6e4626' });
    // estado à direita
    if (has) {
      ui.text(x + 214, y + 20, '✔', { align: 'right', size: 12, bold: true, color: '#2f6b3c' });
    } else if (!can) {
      ui.text(x + 214, y + 20, '🔒', { align: 'right', size: 9, color: '#8c2f1f' });
      ui.text(x + 214, y + 31, i18n.t('ui.skill_only', { spec: i18n.t('spec.' + ab.spec) }),
        { align: 'right', size: 6, color: '#8c2f1f' });
    } else {
      ui.text(x + 214, y + 20, '+', { align: 'right', size: 13, bold: true, color: '#4fa562' });
    }
    ctx.globalAlpha = 1;
    if (can) ui.region('abeq_' + ab.id, x, y, 226, 40);
  });
}

// ---------- Textos DOM ----------
function applyTexts() {
  if (titleEl) titleEl.textContent = i18n.t('app.title');
  if (subtitleEl) subtitleEl.textContent = i18n.t('app.subtitle');
  if (settingsTitleEl) settingsTitleEl.textContent = i18n.t('settings.title');
  if (settingsLangLabelEl) settingsLangLabelEl.textContent = i18n.t('settings.language');
  // destaca o idioma ativo no seletor
  const pt = i18n.lang === 'pt-BR';
  langPtBtn?.classList.toggle('active', pt);
  langEnBtn?.classList.toggle('active', !pt);
  updateStatus();
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
function openSettings() { settingsModal.classList.remove('hidden'); }
function closeSettings() { settingsModal.classList.add('hidden'); }

function chooseLang(lang) {
  i18n.setLang(lang);
  state.language = i18n.lang;
  saveGame(currentSave());
  applyTexts();
}

settingsBtn?.addEventListener('click', openSettings);
settingsClose?.addEventListener('click', closeSettings);
// fecha ao tocar fora do painel
settingsModal?.addEventListener('click', (e) => {
  if (e.target === settingsModal) closeSettings();
});
langPtBtn?.addEventListener('click', () => chooseLang('pt-BR'));
langEnBtn?.addEventListener('click', () => chooseLang('en'));

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
  // salvamento desativado no desenvolvimento: qualquer save velho
  // de versões anteriores é descartado — a vila começa do zero.
  if (!SAVE_ENABLED) clearGame();
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
  else if (demo === 'construction') {
    // Prévia visual da lona: o construtor já está no canteiro para que a
    // poeira e o cronômetro possam ser vistos em screenshots/testes.
    const site = village.beginBuildAt('house', 850, 760);
    if (site) {
      const builder = assignBuilder(site);
      if (builder) {
        builder.x = site.x - 15; builder.y = site.y + 4;
        builder.job.type = 'build';
        site.construction.working = true;
      }
      camera.x = site.x; camera.y = site.y - 4; camera.zoom = 1.4;
    }
  }
  else if (demo === 'jobs') state.screen = 'jobs';
  else if (demo === 'quests') state.screen = 'quests';
  else if (demo === 'kitchen') state.screen = 'kitchen';
  else if (demo === 'market') {
    // a prévia precisa do Mercado de pé: destrava e constrói na hora
    if (!village.has('mercado')) {
      village.level = Math.max(village.level, BUILDINGS.mercado.reqLevel);
      village.res.wood += 999; village.res.stone += 999; village.res.gold += 999;
      village.build('mercado');
    }
    ensureArmazem();          // p/ a prateleira de equipamentos aparecer
    village.addItem('espada_ferro', 2);   // e algo de equipamento p/ revender
    openMarket();
  }
  else if (demo === 'armazem') {
    // a prévia precisa do Armazém de pé: destrava e constrói na hora
    ensureArmazem();
    village.addItem('peitoral_avaritia', 1);
    village.addItem('anel_rubi', 2);
    village.addItem('clava_goblin', 1);
    village.meals = { bread: 3, soup: 1, stew: 2, feast: 1 };
    state.screen = 'armazem';
  }
  else if (demo === 'equip') {
    ensureArmazem();
    // dá umas peças para a prévia ter o que equipar
    village.addItem('capacete_ferro', 1);
    village.addItem('peitoral_ferro', 1);
    village.addItem('espada_ferro', 1);
    village.addItem('anel_cobre', 2);
    village.addItem('escudo_madeira', 1);
    village.addItem('runa_azul', 1);
    // e um prato + goblin ferido p/ a aba Alimentos
    village.meals.bread = 1;
    village.goblins[0].hp = Math.max(1, Math.floor(village.goblins[0].maxHp * 0.3));
    openEquip(0, 'armazem');
  }
  else if (demo === 'deities') {
    // Mostra as duas divindades lado a lado, já prontas para animar.
    village.level = Math.max(village.level, 3);
    village.res.wood += 999; village.res.stone += 999; village.res.gold += 999;
    if (!village.has('grande_arvore')) village.build('grande_arvore');
    if (!village.has('golem_pedra')) village.build('golem_pedra');
    deities.sync();
    camera.x = world.clearing.x; camera.y = world.clearing.y; camera.zoom = 1.2;
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
  const bootMsg = document.getElementById('bootMsg');
  if (bootMsg?.remove) bootMsg.remove();   // sumiu o "carregando…"
  requestAnimationFrame(loop);
}

init();

// Alça para os testes (tools/boot_test.mjs): deixa inspecionar e
// semear o estado vivo sem passar por saves. Inofensivo no browser
// (o loader dá um `module` vazio a cada arquivo).
module.exports = {
  get state() { return state; },
  get village() { return village; },
  get world() { return world; },
  get nodes() { return nodes; },
  get deities() { return deities; },
  get camera() { return camera; },
  get quests() { return quests; },
};
