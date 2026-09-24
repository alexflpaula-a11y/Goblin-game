// ============================================================
// abilities.js — Habilidades que os goblins podem equipar.
//
// Parte 2 trará as batalhas por turnos; por enquanto as
// habilidades são escolhas visuais (2 espaços por goblin):
// cada goblin pode equipar as habilidades da própria
// especialidade + as genéricas (spec: null).
//
// goblin.skills = [ 'investida', null ]  (2 espaços)
// ============================================================

// Quantos espaços de habilidade cada goblin tem.
const SKILL_SLOTS = 2;

// Catálogo: `spec` null = qualquer goblin pode equipar.
const ABILITIES = [
  { id: 'golpe_brutal', spec: 'warrior', icon: 'skill_golpe_brutal' },
  { id: 'muralha_ferro', spec: 'warrior', icon: 'skill_muralha_ferro' },
  { id: 'bola_fogo', spec: 'mage', icon: 'skill_bola_fogo' },
  { id: 'raio_gelido', spec: 'mage', icon: 'skill_raio_gelido' },
  { id: 'toque_curativo', spec: 'healer', icon: 'skill_toque_curativo' },
  { id: 'rezo', spec: 'healer', icon: 'skill_rezo' },
  { id: 'tempero_secreto', spec: 'cook', icon: 'skill_tempero_secreto' },
  { id: 'braco_forte', spec: 'worker', icon: 'skill_braco_forte' },
  { id: 'passo_leve', spec: 'runner', icon: 'skill_passo_leve' },
  { id: 'investida', spec: null, icon: 'skill_investida' },
];

const byId = (id) => ABILITIES.find((a) => a.id === id) || null;

/** Este goblin pode equipar essa habilidade? */
function canEquip(goblin, ability) {
  if (!goblin || !ability) return false;
  return ability.spec == null || ability.spec === goblin.specialty;
}

/** A habilidade já está em algum espaço do goblin? */
function hasAbility(goblin, abilityId) {
  return (goblin.skills || []).includes(abilityId);
}

/**
 * Equipa a habilidade num espaço (0..SKILL_SLOTS-1).
 * Se o espaço estiver ocupado, a antiga é esquecida.
 * Retorna true se equipou (ou já estava equipada).
 */
function equipAbility(goblin, slotIdx, abilityId) {
  const ab = byId(abilityId);
  if (!ab || !canEquip(goblin, ab)) return false;
  goblin.skills = Array.from({ length: SKILL_SLOTS }, (_, i) => goblin.skills?.[i] ?? null);
  if (goblin.skills.includes(abilityId)) {
    // já sabe: apenas move para o espaço escolhido
    goblin.skills = goblin.skills.map((s) => (s === abilityId ? null : s));
  }
  goblin.skills[slotIdx] = abilityId;
  return true;
}

/** Remove a habilidade de um espaço (se houver). */
function unequipAbility(goblin, slotIdx) {
  goblin.skills = Array.from({ length: SKILL_SLOTS }, (_, i) => goblin.skills?.[i] ?? null);
  const cur = goblin.skills[slotIdx];
  goblin.skills[slotIdx] = null;
  return cur;
}

/** Primeiro espaço livre (ou -1). */
function freeSlot(goblin) {
  for (let i = 0; i < SKILL_SLOTS; i++) {
    if (!goblin.skills?.[i]) return i;
  }
  return -1;
}

module.exports = {
  SKILL_SLOTS, ABILITIES,
  byId, canEquip, hasAbility, equipAbility, unequipAbility, freeSlot,
};
