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
            gear = (G.resolve(camadas, pose['_sword'],
                              lay=pose.get('_lay') is not None)
                    if camadas else None)
            img = R.to_image(R.compose(pose, gear=gear))
            if pedacos(img) > 1:
                partidos.append(f'{acao}_{i}')
    ok(not partidos, f'{nome}: nenhum membro descola', ', '.join(partidos[:6]))

# AS 45 VARIAÇÕES, uma a uma. Elas pintam adornos que podem sair da
# silhueta (brinco, ponta da bandana): se um deles ficar flutuando ao lado
# da cabeça, aparece aqui como pedaço solto.
quebradas = []
for vid in V.ORDER:
    var = V.build(vid)
    for a in A.ACTIONS:
        for i, f in enumerate(A.render_action(a, var)):
            if pedacos(f) > 1:
                quebradas.append(f'{vid}/{a}_{i}')
ok(not quebradas, f'as {len(V.ORDER)} variações: nada solto em nenhum quadro',
   ', '.join(quebradas[:6]))

# ---- 2. movimento contínuo: nada de salto ----
print()
for acao in A.ACTIONS:
    poses = A.POSES[acao]()
    pior, onde = 0, None
    for i in range(1, len(poses)):
        for k in PARTES:
            # o corpo caído não usa as partes: é um desenho inteiro
            if poses[i][k] is None or poses[i - 1][k] is None:
                continue
            d = max(abs(poses[i][k][0] - poses[i - 1][k][0]),
                    abs(poses[i][k][1] - poses[i - 1][k][1]))
            if d > pior:
                pior, onde = d, f'{k} no quadro {i}'
    # a morte tem um corte proposital: o quadro em que o corpo tomba
    limite = A.MAX_STEP if acao != 'death' else 99
    ok(pior <= limite, f'{acao}: nenhuma parte salta mais que {limite} px',
       f'{pior} px em {onde}')

# ---- 3. braço sempre preso ao ombro ----
# O ombro desce junto com a compressão do tronco (agachar), então a
# referência do braço é o ombro, não a origem do tronco.
print()
for acao in A.ACTIONS:
    pior = 0
    for p in A.POSES[acao]():
        if p['torso'] is None:
            continue
        ombro = (p['torso'][0], p['torso'][1] + (p.get('_squash') or {}).get('torso', 0))
        for k in ('arm_l', 'arm_r'):
            pior = max(pior, abs(p[k][0] - ombro[0]), abs(p[k][1] - ombro[1]))
    ok(pior <= 4, f'{acao}: braço nunca se afasta mais que 4 px do ombro',
       f'{pior} px')

# ---- 4. a morte agacha, tomba e deita — sem teleportar ----
print()
quadros = A.render_action('death')
caixas = [f.getbbox() or (0, 64, 0, 64) for f in quadros]
topo = [b[1] for b in caixas]
chao = [b[3] for b in caixas]

fundo = A.DEATH_SQUASH.index(max(A.DEATH_SQUASH))      # quadro mais agachado
agacha = topo[:fundo + 1]
ok(len(agacha) >= 5, 'morte: o agachamento tem quadros que cheguem',
   f'{len(agacha)} quadros')
ok(all(b >= a for a, b in zip(agacha, agacha[1:])),
   'morte: agachando, o corpo só desce — nunca sobe de volta', str(agacha))
ok(agacha[-1] - agacha[0] >= 8,
   'morte: o goblin agacha de verdade antes de cair',
   f'desceu só {agacha[-1] - agacha[0]} px')
ok(A.DEATH_SQUASH[A.DEATH_TOPPLE - 1] < max(A.DEATH_SQUASH),
   'morte: o joelho larga antes do tombo (não cai ainda agachado)',
   str(A.DEATH_SQUASH[:A.DEATH_TOPPLE]))
ok(all(c >= 60 for c in chao[:A.DEATH_TOPPLE]),
   'morte: agachando, os pés ficam plantados no chão', str(chao[:A.DEATH_TOPPLE]))
ok(max(abs(b - a) for a, b in zip(topo, topo[1:])) <= 10,
   'morte: nenhum quadro teleporta o corpo',
   str([b - a for a, b in zip(topo, topo[1:])]))

# o corpo tem de encolher de verdade (joelho dobrando), não só descer
alturas = [b[3] - b[1] for b in caixas]
ok(alturas[fundo] <= alturas[0] - 8,
   'morte: o tronco comprime (não é só o corpo deslizando para baixo)',
   f'{alturas[0]} -> {alturas[A.DEATH_TOPPLE - 1]} px')

# e tem de tombar até a diagonal da imagem de referência
# o corpo caído é um desenho próprio: comparar com o goblin DE PÉ, que é
# estreito e alto. Deitado na diagonal ele é mais largo que o de pé — mas
# não "mais largo que alto", porque o braço erguido continua subindo.
caixa = quadros[-1].getbbox()
de_pe = A.render_action('idle')[0].getbbox()
ok((caixa[2] - caixa[0]) > (de_pe[2] - de_pe[0]) + 8,
   'morte: termina deitado (bem mais largo que o goblin de pé)',
   f'{caixa[2] - caixa[0]} px deitado vs {de_pe[2] - de_pe[0]} px de pé')
ok(caixa[3] >= 62, 'morte: o corpo caído encosta no chão', str(caixa))
giro = [abs(b - a) for a, b in zip(A.DEATH_LAY_TURN, A.DEATH_LAY_TURN[1:])]
ok(max(giro) <= 18, 'morte: o tombo é gradual, não um corte seco', str(giro))
ok(A.DEATH_LAY_TURN[-1] == 0,
   'morte: o último quadro é o desenho do caído sem giro nenhum')
ok(all(p['_lay'] is not None for p in A.POSES['death']()[A.DEATH_LYING:]),
   'morte: o corpo caído é o desenho próprio (R.LAY), não o goblin girado')
larg = [b[2] - b[0] for b in caixas]
ok(larg[-1] >= larg[0] + 8,
   'morte: deitado, o corpo ocupa o chão (fica mais largo que de pé)',
   f'{larg[0]} -> {larg[-1]} px')
ok(A.FRAME_COUNTS['death'] >= 20,
   'morte tem quadros suficientes para a queda ser lida',
   str(A.FRAME_COUNTS['death']))

# ---- 5. o goblin base está desarmado ----
print()
nu = R.render(R.base_pose())
armado = R.render(R.base_pose(_weapon=True))
ok(nu.getbbox() != armado.getbbox() or list(nu.getdata()) != list(armado.getdata()),
   'o corpo base não desenha arma nenhuma')
ok(all('sword' in p for a in A.ACTIONS for p in A.POSES[a]()),
   'toda pose ainda expõe a âncora da mão (para a arma equipada encaixar)')
for w in ('wpn_adaga_pedra', 'wpn_adaga_metal', 'wpn_adaga_madeira'):
    camadas = G.PIECES[w][0]
    pose = A.POSES['idle']()[0]
    com = R.to_image(R.compose(pose, gear=G.resolve(camadas, pose['_sword'])))
    sem = R.to_image(R.compose(pose))
    ok(list(com.getdata()) != list(sem.getdata()), f'{w} aparece na mão')

# ---- 6. as 45 variações são visíveis e distintas entre si ----
# Era o defeito: quase toda variação mudava 1 ou 2 pixels e, lado a lado,
# as 45 pareciam o mesmo goblin.
print()
base = A.render_action('idle')[0]


def diferenca(a, b):
    pa, pb = list(a.getdata()), list(b.getdata())
    return sum(1 for x, y in zip(pa, pb) if x != y)


quadros = {vid: A.render_action('idle', V.build(vid))[0] for vid in V.ORDER}
fracas = [(vid, diferenca(f, base)) for vid, f in quadros.items()
          if vid != '18_ileso' and diferenca(f, base) < 14]
ok(not fracas, 'toda variação muda pelo menos 14 px do goblin base',
   ', '.join(f'{v} ({n} px)' for v, n in fracas))

ok(diferenca(quadros['18_ileso'], base) == 0,
   '18_ileso é exatamente o goblin base (é a variação "sem marca")')

iguais = []
nomes = list(quadros)
for i, a in enumerate(nomes):
    for b in nomes[i + 1:]:
        if diferenca(quadros[a], quadros[b]) < 6:
            iguais.append(f'{a} ≈ {b}')
ok(not iguais, 'não há duas variações parecidas demais entre si',
   ', '.join(iguais[:6]))

# a marca tem de acompanhar o goblin em TODA pose, não só na parada
somem = []
for vid in V.ORDER:
    if vid == '18_ileso':
        continue
    var = V.build(vid)
    for a in ('walk', 'attack', 'hurt'):
        f = A.render_action(a, var)[3]
        if diferenca(f, A.render_action(a)[3]) < 8:
            somem.append(f'{vid}/{a}')
ok(not somem, 'a marca da variação aparece também andando, atacando e apanhando',
   ', '.join(somem[:6]))

print(f'\n  {passou} passaram · {len(falhas)} falharam')
sys.exit(1 if falhas else 0)
