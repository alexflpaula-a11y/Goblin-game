#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_conjunto.py — compõe as versões do conjunto AVARITIA:

  sprites/itens/conjunto_avaritia/        ← 3 peças juntas (armadura completa)
  sprites/itens/combo_capacete_peitoral/  ← pares
  sprites/itens/combo_capacete_calca/
  sprites/itens/combo_peitoral_calca/

 (as peças SEPARADAS ficam nas próprias pastas: capacete_avaritia/,
  peitoral_avaritia/, calca_avaritia/ — geradas pelo gerar_item.py)

 Regras:
  • zonas disjuntas por construção (assert pixel a pixel);
  • conjunto COMPLETO: tudo PRETO abaixo do elmo (braços, mãos, cinto,
    pernas) — só as ORELHAS ficam verdes; pares mantêm a pele à mostra;
  • guarda de rosto: capacete fechado cobre o rosto por design (visor teal).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gerar_item as G

REPO = G.REPO

PECAS = [('capacete_avaritia', 'cabeca'),
         ('peitoral_avaritia', 'torso'),
         ('calca_avaritia', 'pernas')]

COMBOS = {
    'combo_capacete_peitoral': ['capacete_avaritia', 'peitoral_avaritia'],
    'combo_capacete_calca':    ['capacete_avaritia', 'calca_avaritia'],
    'combo_peitoral_calca':    ['peitoral_avaritia', 'calca_avaritia'],
    'conjunto_avaritia':       ['capacete_avaritia', 'peitoral_avaritia',
                                'calca_avaritia'],
}


def compoe(frames, ids, blackout_total):
    out = None
    for name, base in sorted(frames.items()):
        px = base.load()
        eyes = G.olhos_px(px)
        if eyes:
            ex = sum(p[0] for p in eyes) / len(eyes)
            ey = sum(p[1] for p in eyes) / len(eyes)
        else:
            ex = ey = None
        im = base
        usados = {}
        dome_top = None
        ear_skip = set()
        for _id, zona in PECAS:
            if _id not in ids:
                continue
            cfg = next(c for c in G.ITENS if c['id'] == _id)
            chave = cfg['duplicados'].get(name, name)
            if chave in cfg['mascaras_deitadas']:
                mask = {int(y): list(xs)
                        for y, xs in cfg['mascaras_deitadas'][chave].items()}
            elif zona == 'cabeca' and cfg.get('tampa_rosto'):
                mask = G.mascara_cabeca_fechada_em_pe(px)
            elif zona == 'cabeca':
                mask = G.mascara_cabeca_em_pe(px, ex, ey)
            elif zona == 'torso':
                mask = G.mascara_torso_em_pe(px, ex, ey)
            else:
                mask = G.mascara_pernas_em_pe(px, ey)
            for y, xs in mask.items():
                for x in xs:
                    assert (x, y) not in usados, \
                        'sobreposição em %s (%s)' % ((x, y), name)
                    usados[(x, y)] = _id
            im = G.pinta_avaritia(im, mask, zona, chave in cfg['mascaras_deitadas'])
            if zona == 'cabeca':
                dome_top = min(mask)            # topo do elmo (orelhas acima)
                if cfg.get('tampa_rosto'):
                    ipx = im.load()             # visor teal + boca coberta
                    for (x, y) in G.olhos_px(px):
                        ipx[x, y] = G.A_T
                    for (x, y) in G.boca_px(px):
                        ipx[x, y] = G.R_K
                    # passo 2: orelhas consertadas (verde por cima do preto)
                    ear_skip = G.restaura_orelhas(im, px)
                    if not ear_skip:
                        # deitado: a orelha pode estar NA linha do topo da
                        # máscara (fora dela) — preserva esses verdes
                        ear_skip = {(x, y) for y in (dome_top, dome_top + 1)
                                    for x in range(32)
                                    if (x, y) not in usados
                                    and px[x, y][3] >= 40
                                    and px[x, y][:3] in G.GREENS}

        # ARMADURA COMPLETA: tudo PRETO exceto as ORELHAS (que pontam para
        # fora da cúpula do elmo).
        if blackout_total and dome_top is not None:
            ipx = im.load()
            skip = ear_skip
            for y in range(dome_top, 32):
                for x in range(32):
                    if (x, y) in skip:
                        continue
                    p = ipx[x, y]
                    if p[3] >= 40 and (p[:3] in G.GREENS or p[:3] in G.BROWNS):
                        ipx[x, y] = G.R_K

        anim = '_'.join(name.split('_')[1:-1]); idx = int(name.split('_')[-1])
        if out is None:
            out = []
        out.append((anim, idx, im))
    return out


def main():
    frames = G.extrai_frames()
    for pasta, ids in COMBOS.items():
        outdir = os.path.join(REPO, 'sprites', 'itens', pasta)
        os.makedirs(outdir, exist_ok=True)
        completo = pasta == 'conjunto_avaritia'
        ger = compoe(frames, ids, completo)
        for anim, idx, im in ger:
            im.save(os.path.join(outdir, 'goblin_%s_%d.png' % (anim, idx)))
        print('%-24s %d frames (zonas disjuntas ✓)%s' %
              (pasta + ':', len(ger), ' — blackout total' if completo else ''))


if __name__ == '__main__':
    main()
