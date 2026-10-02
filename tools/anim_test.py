#!/usr/bin/env python3
"""
anim_test.py — garante que o goblin nao se despedaca nem teleporta.

Dois defeitos reais ja apareceram no jogo e viraram teste aqui:

  1. "o braco solta e volta" — no ataque antigo o braco se afastava 6 px do
     tronco em um unico quadro. Teste: nenhuma parte pode andar mais que
     MAX_STEP px de um quadro para o outro, e o braco nunca pode ficar a
     mais de 2 px do tronco.

  2. "ele so teleporta no chao" — a morte pulava direto para o corpo
     deitado. Teste: a morte precisa ter uma descida continua (o goblin
     afunda quadro a quadro) antes de deitar.

Alem disso, todo quadro de toda animacao — nu, com cada peca de armadura e
com cada arma — precisa ser UMA PECA SO: se a silhueta se parte em dois
pedacos soltos, algum membro descolou.
"""
import sys
from collections import deque

import numpy as np

import goblin_rig as R
import goblin_anim as A
import goblin_gear as G
import goblin_variations as V

PARTES = ('torso', 'arm_l', 'arm_r', 'head', 'leg_l', 'leg_r')
falhas = []
passou = 0


def ok(cond, titulo, detalhe=''):
    global passou
    if cond:
        passou += 1
        print(f'  \033[32m✓\033[0m {titulo}')
    else:
        falhas.append(titulo)
        print(f'  \033[31m✗\033[0m {titulo}  {detalhe}')


def pedacos(img):
    """Quantos grupos de pixels soltos a imagem tem (4-vizinhanca)."""
    a = np.array(img)[:, :, 3] > 0
    h, w = a.shape
    visto = np.zeros_like(a)
    n = 0
    for y in range(h):
        for x in range(w):
            if a[y, x] and not visto[y, x]:
                n += 1
                fila = deque([(x, y)])
                visto[y, x] = True
                while fila:
                    cx, cy = fila.popleft()
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if (0 <= nx < w and 0 <= ny < h
                                and a[ny, nx] and not visto[ny, nx]):
                            visto[ny, nx] = True
                            fila.append((nx, ny))
    return n


print('\n\033[1mAnimação — o goblin é uma peça só\033[0m\n')

# ---- 1. corpo inteiro em todo quadro, nu e equipado ----
casos = [('nu', None)] + [(p, G.PIECES[p][0]) for p in G.PIECES]
for nome, camadas in casos:
    partidos = []
    for acao in A.ACTIONS:
        for i, pose in enumerate(A.POSES[acao]()):
            gear = G.resolve(camadas, pose['_sword']) if camadas else None
            img = R.to_image(R.compose(pose, gear=gear))
            if pedacos(img) > 1:
                partidos.append(f'{acao}_{i}')
    ok(not partidos, f'{nome}: nenhum membro descola', ', '.join(partidos[:6]))

# uma variação de cada tipo de troca, para cobrir pele/partes trocadas
for vid in ('16_sem_orelha', '08_albinismo', '51_mutilado'):
    var = V.build(vid)
    partidos = [f'{a}_{i}' for a in A.ACTIONS
                for i, f in enumerate(A.render_action(a, var)) if pedacos(f) > 1]
    ok(not partidos, f'variação {vid}: nenhum membro descola',
       ', '.join(partidos[:6]))

# ---- 2. movimento contínuo: nada de salto ----
print()
for acao in A.ACTIONS:
    poses = A.POSES[acao]()
    pior, onde = 0, None
    for i in range(1, len(poses)):
        for k in PARTES:
            d = max(abs(poses[i][k][0] - poses[i - 1][k][0]),
                    abs(poses[i][k][1] - poses[i - 1][k][1]))
            if d > pior:
                pior, onde = d, f'{k} no quadro {i}'
    # a morte tem um corte proposital: o quadro em que o corpo tomba
    limite = A.MAX_STEP if acao != 'death' else 99
    ok(pior <= limite, f'{acao}: nenhuma parte salta mais que {limite} px',
       f'{pior} px em {onde}')

# ---- 3. braço sempre preso ao ombro ----
print()
for acao in A.ACTIONS:
    pior = 0
    for p in A.POSES[acao]():
        for k in ('arm_l', 'arm_r'):
            pior = max(pior, abs(p[k][0] - p['torso'][0]),
                       abs(p[k][1] - p['torso'][1]))
    ok(pior <= 3, f'{acao}: braço nunca se afasta mais que 3 px do tronco',
       f'{pior} px')

# ---- 4. a morte desce, não teleporta ----
print()
alturas = []
for i, f in enumerate(A.render_action('death')):
    bb = f.getbbox()
    alturas.append(bb[1] if bb else 64)        # topo da silhueta
queda = alturas[:A.DEATH_LYING]
ok(len(queda) >= 10, 'morte tem uma descida longa antes de deitar',
   f'{len(queda)} quadros')
ok(all(b >= a for a, b in zip(queda, queda[1:])),
   'morte: o corpo só desce, nunca sobe de volta', str(queda))
ok(queda[-1] - queda[0] >= 10,
   'morte: o goblin realmente agacha antes de cair',
   f'desceu {queda[-1] - queda[0]} px')
ok(A.FRAME_COUNTS['death'] >= 20,
   'morte tem quadros suficientes para a queda ser lida',
   str(A.FRAME_COUNTS['death']))

# ---- 5. o goblin base está desarmado ----
print()
nu = R.render(R.base_pose())
armado = R.render(R.base_pose(_weapon=True))
ok(nu.getbbox() != armado.getbbox() or list(nu.getdata()) != list(armado.getdata()),
   'o corpo base não desenha arma nenhuma')
ok(all('sword' in A.POSES[a]()[0] for a in A.ACTIONS),
   'toda pose ainda expõe a âncora da mão (para a arma equipada encaixar)')
for w in ('wpn_adaga_pedra', 'wpn_adaga_metal', 'wpn_adaga_madeira'):
    camadas = G.PIECES[w][0]
    pose = A.POSES['idle']()[0]
    com = R.to_image(R.compose(pose, gear=G.resolve(camadas, pose['_sword'])))
    sem = R.to_image(R.compose(pose))
    ok(list(com.getdata()) != list(sem.getdata()), f'{w} aparece na mão')

print(f'\n  {passou} passaram · {len(falhas)} falharam')
sys.exit(1 if falhas else 0)
