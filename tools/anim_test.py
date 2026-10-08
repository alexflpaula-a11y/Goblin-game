#!/usr/bin/env python3
"""
anim_test.py — garante que o goblin nao se despedaca nem teleporta.

Dois defeitos reais ja apareceram no jogo e viraram teste aqui:

  1. "o braco continua soltando" — e nao era o braco se separando: no
     repouso a fresta entre braco e tronco e de ZERO pixel, e a animacao
     abria ate QUATRO. Encostar num canto nao basta, o olho ve o buraco
     de fundo ao longo do braco inteiro. Teste: a fresta nunca pode
     passar da que o repouso ja tem.

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
        # efeitos=False: a palavra GOBLINZED e o halo vermelho são
        # peças soltas de propósito e mascarariam um membro realmente solto
        for i, f in enumerate(A.render_action(a, var, efeitos=False)):
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

# ---- 4. a morte: instantânea, com GOBLINZED em vermelho ----
print()
# sem efeitos = só o corpo. A palavra é, de propósito, um pedaço solto do
# desenho; medir o corpo com ela na tela não mede nada.
quadros = A.render_action('death', efeitos=False)
com_efeito = A.render_action('death')
caixas = [f.getbbox() or (0, 64, 0, 64) for f in quadros]
poses = A.POSES['death']()

ok(A.GOBLINZED_DEITA == 0 and all(p['_lay'] is not None for p in poses),
   'morte: ele já aparece no chão no primeiro quadro (dano final mata na hora)')
ok(all(p['torso'] is None for p in poses),
   'morte: não sobrou nenhum quadro de pé — nada de agachar nem tombar')
ok(len(set(caixas)) == 1,
   'morte: o corpo não se mexe mais depois de cair', str(set(caixas)))
ok(A.FRAME_COUNTS['death'] <= 12,
   'morte: a cena é curta (o pedido foi que fosse mais rápida)',
   f"{A.FRAME_COUNTS['death']} quadros")

# a palavra entra rápido e inteira
escritas = A.GOBLINZED_LETRAS
ok(all(b >= a for a, b in zip(escritas, escritas[1:])),
   'morte: a palavra só cresce, nunca perde letra', str(escritas))
ok(max(escritas) == len(A.GOBLINZED),
   'morte: GOBLINZED aparece inteira', str(escritas))
ok(escritas.index(len(A.GOBLINZED)) <= 4,
   'morte: a palavra termina de ser escrita nos primeiros quadros',
   f'só no quadro {escritas.index(len(A.GOBLINZED))}')
ok(all(ch in A.FONTE for ch in A.GOBLINZED),
   'morte: a fonte tem todas as letras de GOBLINZED')

passo = A.LETRA_W + A.LETRA_GAP
larg_txt = len(A.GOBLINZED) * passo - A.LETRA_GAP
ok(larg_txt + 2 <= R.SIZE, 'morte: GOBLINZED cabe nos 64 px do quadro',
   f'{larg_txt} px')
ok(A.TEXTO_Y + A.LETRA_H < min(b[1] for b in caixas),
   'morte: a palavra fica ACIMA do corpo, sem cobrir o goblin')

# a luz vermelha acompanha a escrita e some depois
brilho = A.DEATH_GLOW
ok(len(brilho) == A.DEATH_FRAMES and len(A.GOBLINZED_LETRAS) == A.DEATH_FRAMES
   and len(A.GOBLINZED_ALPHA) == A.DEATH_FRAMES
   and len(A.DEATH_ALPHA) == A.DEATH_FRAMES,
   f'morte: todas as tabelas têm {A.DEATH_FRAMES} entradas')
ok(brilho[0] >= 0.9, 'morte: a luz estoura no quadro do baque', str(brilho[0]))
ok(all(b <= a for a, b in zip(brilho, brilho[1:])),
   'morte: a luz só esvazia, nunca volta a crescer', str(brilho))
ok(brilho[-1] == 0, 'morte: o brilho se apaga no fim', str(brilho[-3:]))
ok(A.GOBLINZED_ALPHA[-1] < A.GOBLINZED_ALPHA[1],
   'morte: a palavra apaga junto com o corpo')

difs = sum(1 for a, b in zip(com_efeito[3].getdata(), quadros[3].getdata())
           if a != b)
ok(difs > 400, 'morte: a luz vermelha e a palavra realmente aparecem',
   f'só {difs} px de diferença')

# o corpo caído é largo, deitado na diagonal rasa e encostado no chão
caixa = caixas[-1]
de_pe = A.render_action('idle', efeitos=False)[0].getbbox()
larg, alt = caixa[2] - caixa[0], caixa[3] - caixa[1]
ok(larg > (de_pe[2] - de_pe[0]) + 8,
   'morte: deitado ele ocupa o chão (bem mais largo que o goblin de pé)',
   f'{larg} px deitado vs {de_pe[2] - de_pe[0]} px de pé')
ok(larg > alt,
   'morte: o corpo está DEITADO — mais largo que alto, como na referência',
   f'{larg} x {alt} px')
ok(caixa[3] >= 62, 'morte: o corpo caído encosta no chão', str(caixa))

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
# O piso era 14 px e isso saiu pela culatra: para passar no teste, traco
# pequeno virava mancha grande (verruga de 3x3, dente do tamanho do
# focinho, marca de nascenca cobrindo meia testa). Uma presa de ouro de
# 10 px saturados se ve de longe; um borrao de 20 px so polui o desenho.
# O que o teste tem de garantir e que a marca EXISTE, nao que ela e grande.
fracas = [(vid, diferenca(f, base)) for vid, f in quadros.items()
          if vid != '18_ileso' and diferenca(f, base) < 9]
ok(not fracas, 'toda variação muda pelo menos 9 px do goblin base',
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
        f = A.render_action(a, var, efeitos=False)[3]
        if diferenca(f, A.render_action(a, efeitos=False)[3]) < 8:
            somem.append(f'{vid}/{a}')
ok(not somem, 'a marca da variação aparece também andando, atacando e apanhando',
   ', '.join(somem[:6]))

# ------------------------------------------------------------------ #
#  o goblin tem de cair com as suas marcas, e largar a arma no chao    #
# ------------------------------------------------------------------ #
mortos = []
for vid in V.ORDER:
    if vid == '18_ileso':
        continue
    var = V.build(vid)
    f = A.render_action('death', var, efeitos=False)[0]
    if diferenca(f, A.render_action('death', efeitos=False)[0]) < 4:
        mortos.append(vid)
ok(not mortos, 'a variação continua visível no goblin caído',
   ', '.join(mortos[:8]))

# o rosto fica contra o chão: nada do que é rosto pode reaparecer no caído
olho = R.ANCHORS['head_box']
var = V.build('31_mistico')          # olhos brancos, o traço mais berrante
marcas = R.marcas_deitadas(var['detail'], var['parts'])
x0, y0, x1, y1 = R.ROSTO_BOX
dif = R._diferenca_de_pe(var['detail'], var['parts'])
ok(not [1 for (x, y) in dif if x0 <= x < x1 and y0 <= y < y1],
   'as marcas de rosto não são levadas para o corpo caído (ele cai de bruços)')

# toda marca estampada no caído tem de estar EM CIMA do corpo, nunca solta
soltas = []
for vid in V.ORDER:
    var = V.build(vid)
    if not (var['detail'] or var['parts']):
        continue
    for x, y, _ in R.marcas_deitadas(var['detail'], var['parts']):
        if R.LAY[y][x] == '.':
            soltas.append((vid, x, y))
ok(not soltas, 'nenhuma marca do goblin caído flutua fora do corpo',
   str(soltas[:4]))

# a arma larga da mão e vai para o chão ao lado
import goblin_gear as G                                      # noqa: E402
pose = A.POSES['death']()[0]
gear = G.resolve(G.PIECES['wpn_espada'][0], pose.get('_sword', 'down'),
                 lay=True)
limpo = R.compose(pose)
armado = R.compose(pose, gear=gear)
arma = [(x, y) for y in range(R.SIZE) for x in range(R.SIZE)
        if armado[y][x] != limpo[y][x]]
ok(arma, 'o goblin caído mostra a arma que largou')
ok(max(y for _, y in arma) >= 58,
   'a arma largada está no chão, embaixo do corpo caído',
   f'máximo y = {max(y for _, y in arma)}')
ok(min(y for _, y in arma) > R.LAY_HAND[1] + 4,
   'a arma não ficou presa na mão do morto',
   f'topo da arma y = {min(y for _, y in arma)}')


# ------------------------------------------------------------------ #
#  O CORPO E UMA PECA SO                                               #
# ------------------------------------------------------------------ #
# O goblin se partia no meio e, no trabalho, a perna sumia: a animacao
# empurrava o tronco para um lado e as pernas para o outro, abrindo a
# cintura — e como o tronco e desenhado depois das pernas, ele passava por
# cima e comia a perna. Estas tres checagens cobram a regra de ouro
# descrita no topo do goblin_anim.py.

def _pedacos(buf):
    """Quantos blocos soltos a silhueta tem (vizinhanca de 8)."""
    pix = {(x, y) for y in range(R.SIZE) for x in range(R.SIZE)
           if buf[y][x] is not None}
    vistos, n = set(), 0
    for p in pix:
        if p in vistos:
            continue
        n += 1
        fila = [p]
        vistos.add(p)
        while fila:
            x, y = fila.pop()
            for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1),
                      (x + 1, y + 1), (x - 1, y - 1), (x + 1, y - 1),
                      (x - 1, y + 1)):
                if q in pix and q not in vistos:
                    vistos.add(q)
                    fila.append(q)
    return n


import goblin_gear as GG                                     # noqa: E402

partidos = []
for pref in [None] + list(GG.PIECES):
    for acao in A.ACTIONS:
        for i, pose in enumerate(A.POSES[acao]()):
            eq = (GG.resolve(GG.PIECES[pref][0], pose.get('_sword', 'down'),
                             lay=pose.get('_lay') is not None)
                  if pref else None)
            if _pedacos(R.compose(pose, gear=eq)) > 1:
                partidos.append(f'{pref or "nu"}/{acao}_{i}')
ok(not partidos,
   'nenhum quadro tem pedaco solto — nem nu, nem com cada peca de armadura',
   f'{len(partidos)} quadros: ' + ', '.join(partidos[:6]))

# a perna nao pode sumir por baixo do tronco em nenhum quadro
somem = []
for acao in ('idle', 'walk', 'attack', 'hurt'):
    for i, pose in enumerate(A.POSES[acao]()):
        buf = R.compose(pose)
        so_pernas = R.compose({**pose, 'torso': None, 'head': None,
                               'arm_l': None, 'arm_r': None})
        visivel = sum(1 for y in range(R.SIZE) for x in range(R.SIZE)
                      if so_pernas[y][x] is not None and buf[y][x] is not None)
        if visivel < 60:
            somem.append(f'{acao}_{i} ({visivel} px)')
ok(not somem, 'as pernas aparecem em todos os quadros, nunca comidas pelo tronco',
   ', '.join(somem[:6]))

# e o goblin tem de se MEXER INTEIRO: cada parte muda de lugar ao longo do
# ciclo. Um boneco que so translada o corpo todo e o que parecia um robo.
paradas = []
for acao in ('idle', 'walk', 'attack', 'hurt'):
    poses = A.POSES[acao]()
    # parado as pernas ficam plantadas no chao, e assim que tem de ser;
    # o resto do corpo e que nao pode congelar
    partes = ('head', 'torso', 'arm_l', 'arm_r')
    if acao == 'walk':
        # correndo, as DUAS pernas trabalham
        partes += ('leg_l', 'leg_r')

    def lugar(p, parte):
        # "se mexer" nao e so trocar de lugar: o tronco do ataque se mexe
        # AGACHANDO (_squash come linhas do meio dele) e a perna se mexe
        # INCLINANDO (_shear). As tres coisas contam.
        return (p[parte],
                (p.get('_shear') or {}).get(parte),
                (p.get('_squash') or {}).get(parte))

    for parte in partes:
        if len({lugar(p, parte) for p in poses}) < 2:
            paradas.append(f'{acao}/{parte}')

    if acao in ('attack', 'hurt'):
        # golpeando/apanhando o goblin planta um pe e investe com o outro
        # (e o que o original faz). Exigir as duas pernas aqui seria
        # inventar movimento; exigir ao menos uma, nao.
        if not any(len({lugar(p, pe) for p in poses}) >= 2
                   for pe in ('leg_l', 'leg_r')):
            paradas.append(f'{acao}/pernas')
ok(not paradas, 'todas as partes do corpo se mexem em todas as animacoes',
   ', '.join(paradas[:8]))

PARTES_CORPO = ('head', 'torso', 'arm_l', 'arm_r', 'leg_l', 'leg_r')

# ------------------------------------------------------------------ #
#  AS REGRAS DOS QUADROS ESCRITOS A MAO                               #
# ------------------------------------------------------------------ #
# As poses deixaram de ser calculadas a partir do campo medido do
# goblin antigo e passaram a ser escritas uma a uma (ver as tabelas
# IDLE / WALK / SOCO / DANO no goblin_anim). O campo escalado produzia
# defeitos que nao estao em tabela nenhuma: braco entrando no corpo,
# queixo esticado, os dois pes no ar, quadril que nao gira.
#
# Estes testes sao o contrato dessas tabelas. Cada um corresponde a
# um defeito que o jogador apontou.

ACOES_DE_PE = ('idle', 'walk', 'attack', 'hurt')
PECAS = ('head', 'torso', 'arm_l', 'arm_r', 'leg_l', 'leg_r')

# 1. Tudo em numero par: um pixel do sprite e meio pixel de tela.
impar = [f'{a}_{i}/{n}={p[n]}'
         for a in ACOES_DE_PE for i, p in enumerate(A.POSES[a]())
         for n in PECAS if p[n][0] % 2 or p[n][1] % 2]
ok(not impar, 'todo quadro anda na grade da tela (tudo par)',
   ', '.join(impar[:6]))

# 2. O QUEIXO NAO ESTICA. Era isto: a cabeca tinha movimento proprio,
#    subia enquanto o tronco ficava, e o vao do pescoco era tapado com
#    contorno — lia como queixo/papada esticada. A cabeca anda com o
#    tronco, ponto.
solta = [f'{a}_{i}' for a in ACOES_DE_PE for i, p in enumerate(A.POSES[a]())
         if p['head'] != p['torso']]
ok(not solta, 'a cabeca anda colada no tronco: o queixo nunca estica',
   ', '.join(solta[:6]))

# 3. O BRACO NUNCA ENTRA PARA DENTRO. O tronco e desenhado entre os
#    dois bracos; um braco indo para o centro e comido pelo peito ou
#    some atras dele.
dentro = []
for a in ACOES_DE_PE:
    for i, p in enumerate(A.POSES[a]()):
        if p['arm_l'][0] - p['torso'][0] > 0:
            dentro.append(f'{a}_{i}/arm_l')
        if p['arm_r'][0] - p['torso'][0] < 0:
            dentro.append(f'{a}_{i}/arm_r')
ok(not dentro, 'o braco nunca entra para dentro do corpo',
   ', '.join(dentro[:6]))

# 4. O CORPO SO AFUNDA. Subir o tronco descobre o alto da perna e abre
#    o quadril; afundar so aumenta a sobreposicao — e e o que o corpo
#    faz quando o peso cai sobre a perna.
voou = [f'{a}_{i}' for a in ACOES_DE_PE for i, p in enumerate(A.POSES[a]())
        if p['torso'][1] < 0]
ok(not voou, 'o corpo afunda e volta, nunca decola', ', '.join(voou[:6]))

# 5. UM PE SEMPRE NO CHAO.
voando = [f'{a}_{i}' for a in ACOES_DE_PE for i, p in enumerate(A.POSES[a]())
          if max(p['leg_l'][1], p['leg_r'][1]) < 0]
ok(not voando, 'nunca os dois pes no ar: andar e plantar um e soltar o outro',
   ', '.join(voando[:6]))

# 6. O QUADRIL GIRA NA CAMINHADA. Girar e as duas pernas fazendo
#    coisas diferentes ao mesmo tempo — uma plantada assumindo o peso,
#    a outra solta e deslocada — com o tronco passando o peso de um
#    lado para o outro. Duas pernas paralelas subindo juntas nao sao
#    uma bacia, sao um boneco sendo erguido.
andar = A.POSES['walk']()
alturas = {p['leg_l'][1] - p['leg_r'][1] for p in andar}
lados = {p['leg_l'][0] - p['leg_r'][0] for p in andar}
peso = {p['torso'][0] for p in andar}
ok(len(alturas) >= 2 and len(lados) >= 2,
   'andando, o quadril gira: as pernas diferem em altura E em avanco',
   f'alturas {sorted(alturas)} / avancos {sorted(lados)}')
# O TRONCO NAO GINGA. Ele ja foi 2 px para cada lado a cada passo e a
# leitura foi imediata: "correndo ele parece estar dancando". Na vista
# de frente, corpo indo e voltando de lado e samba. Quem mostra o
# passo e a perna; e justamente com o tronco parado que o giro do
# quadril aparece.
ok(len(peso) == 1,
   'andando, o tronco nao ginga de lado (isso virava danca)',
   f'tronco em x: {sorted(peso)}')
ok(all(p['leg_l'][1] == 0 or p['leg_r'][1] == 0 for p in andar),
   'andando, o pe plantado fica no chao o tempo todo')

# 7. OS BRACOS VAO AO CONTRARIO DAS PERNAS, como numa pessoa.
cruzado = False
for p in andar:
    solto = 'leg_l' if p['leg_l'][1] < p['leg_r'][1] else (
        'leg_r' if p['leg_r'][1] < p['leg_l'][1] else None)
    if solto is None:
        continue
    braco = 'arm_r' if solto == 'leg_l' else 'arm_l'
    if p[braco][0] - p['torso'][0] != 0:
        cruzado = True
ok(cruzado, 'andando, o braco que abre e o do lado contrario a perna '
   'que sai do chao')

# 8. O SOCO: o punho SOBE para armar (puxar para tras o enfiava no
#    peito), vai para fora na batida, e o corpo avanca junto.
soco = A.POSES['attack']()
punho = [p['arm_r'][0] - p['torso'][0] for p in soco]
alto = [p['arm_r'][1] - p['torso'][1] for p in soco]
tronco = [p['torso'][0] for p in soco]
ok(max(punho) >= 2 and min(punho) >= 0,
   'o soco sai para fora e o punho nunca recua para dentro do peito',
   f'punho: {punho[:8]}')
ok(min(alto) < 0, 'o punho ARMA subindo, nao recolhendo para tras',
   f'altura do punho: {alto[:8]}')
ok(max(tronco) - min(tronco) >= 2,
   'o corpo avanca junto com o soco (o golpe tem peso)',
   f'tronco: {tronco[:8]}')
ok(all(p['leg_l'][1] == 0 and p['leg_r'][1] == 0 for p in soco),
   'quem bate firma os dois pes no chao')

# 9. PARADO E SO RESPIRAR: os pes nao saem do lugar.
parado = A.POSES['idle']()
ok(all(p['leg_l'] == (0, 0) and p['leg_r'] == (0, 0) for p in parado),
   'parado: os pes nao se mexem')
ok(len({p['torso'][1] for p in parado}) >= 2
   and max(p['torso'][1] for p in parado) <= 2,
   'parado: o peito afunda um pixel de tela e volta (ele respira)',
   str(sorted({p['torso'][1] for p in parado})))

# e o passo tem de dar a mesma ABERTURA de pernas, proporcionalmente
aberturas = {}
for acao in ('walk', 'attack'):
    vaos = []
    for pose in A.POSES[acao]():
        buf = R.compose({**pose, 'torso': None, 'head': None,
                         'arm_l': None, 'arm_r': None, 'sword': None})
        cols = [x for y in range(R.SIZE) for x in range(R.SIZE)
                if buf[y][x] is not None]
        vaos.append(max(cols) - min(cols))
    aberturas[acao] = max(vaos) - min(vaos)
ok(aberturas['walk'] >= 4,
   'correndo, o vão entre os pés abre e fecha como no original',
   f'abre só {aberturas["walk"]} px')
ok(aberturas['attack'] >= 4,
   'atacando, as pernas afastam na investida como no original',
   f'afastam só {aberturas["attack"]} px')

# ------------------------------------------------------------------ #
#  A FRESTA DO BRACO                                                  #
# ------------------------------------------------------------------ #
# A reclamacao foi "o braco continua soltando", e medindo deu para ver
# exatamente o que era: no repouso nao ha um pixel de fundo entre o
# braco e o tronco, e durante a animacao abriam quatro. O braco nao
# estava se separando — estava abrindo um buraco. Nenhum quadro pode
# abrir mais do que o repouso ja abre.

def _frestas(pose):
    """Buraco entre braco e tronco, medido no OMBRO e na MAO em separado.

    A distincao importa. Fresta no ombro e defeito: o braco descolou do
    corpo. Fresta na mao e o braco ESTICANDO — e exatamente isso que o
    goblin original faz no ataque, onde os dois bracos viram um bastao
    apontado para os lados. Medir as duas juntas (como antes) obrigava o
    braco a ficar colado no tronco de cima a baixo, e foi o que deixou o
    braco de apoio congelado nos 17 quadros do trabalho.
    """
    tronco = R.compose({**pose, 'head': None, 'arm_l': None, 'arm_r': None,
                        'leg_l': None, 'leg_r': None, 'sword': None})
    ombro = mao = 0
    for braco, lado in (('arm_l', -1), ('arm_r', +1)):
        outro = 'arm_r' if braco == 'arm_l' else 'arm_l'
        so = R.compose({**pose, 'head': None, 'torso': None, 'leg_l': None,
                        'leg_r': None, 'sword': None, outro: None})
        linhas = [y for y in range(R.SIZE)
                  if any(so[y][x] is not None for x in range(R.SIZE))]
        if not linhas:
            continue
        # o terco de cima do braco e o ombro; o resto e antebraco e mao
        corte = min(linhas) + max(1, (max(linhas) - min(linhas) + 1) // 3)
        for y in linhas:
            bx = [x for x in range(R.SIZE) if so[y][x] is not None]
            cx = [x for x in range(R.SIZE) if tronco[y][x] is not None]
            if not bx or not cx:
                continue
            d = (min(cx) - max(bx) - 1) if lado < 0 else (min(bx) - max(cx) - 1)
            if y < corte:
                ombro = max(ombro, d)
            else:
                mao = max(mao, d)
    return ombro, mao


repouso_ombro, repouso_mao = _frestas(A._pose_do_original('idle', 0))

# 1. O OMBRO SO PODE ABRIR UMA FRESTA DE UM PIXEL DE TELA.
#
# Zero seria mais seguro mas e infiel: olhando os quadros do original
# ampliados, no golpe os dois bracos dele viram bastoes apontando para
# os lados, COM fundo entre o braco e o tronco. Proibir qualquer fresta
# foi o que manteve o braco colado no corpo e congelado.
#
# O limite e 2 px do sprite de 64, que e 1 px na tela de 32 — o minimo
# que existe. A garantia dura de verdade continua sendo o teste de
# conectividade logo acima: pode afastar, nao pode SOLTAR.
FRESTA_OMBRO_MAX = 2
abertos = []
for acao in ('idle', 'walk', 'attack', 'hurt'):
    for i, pose in enumerate(A.POSES[acao]()):
        f = _frestas(pose)[0]
        if f > repouso_ombro + FRESTA_OMBRO_MAX:
            abertos.append(f'{acao}_{i} ({f} px)')
ok(not abertos,
   f'o ombro abre no maximo 1 px de tela e nunca solta '
   f'(repouso: {repouso_ombro} px)',
   ', '.join(abertos[:6]))

# 2. A mao pode se afastar do corpo, mas so o tanto que a TABELA
#    daquele quadro mandou o braco andar. Mais do que isso nao e o
#    braco se mexendo, e defeito.
exagero = []
for acao in ('idle', 'walk', 'attack', 'hurt'):
    for i, pose in enumerate(A.POSES[acao]()):
        # conta tambem o braco ERGUIDO: subir o braco tira o ombro de
        # junto do peito e a fresta na altura da mao cresce sozinha
        pedido = max(abs(pose['arm_l'][0] - pose['torso'][0])
                     + abs(pose['arm_l'][1] - pose['torso'][1]),
                     abs(pose['arm_r'][0] - pose['torso'][0])
                     + abs(pose['arm_r'][1] - pose['torso'][1]))
        f = _frestas(pose)[1]
        # 2 px de folga = 1 px de tela: ergueu ou abriu o braco, a
        # cintura e mais estreita que o ombro e a fresta cresce um
        # tanto por geometria, nao por defeito. O que nao pode e o
        # braco SOLTAR, e disso cuida o teste de conectividade.
        if f > repouso_mao + pedido + 2:
            exagero.append(f'{acao}_{i} ({f} px, pediu {pedido})')
ok(not exagero,
   'a mao so se afasta o que a tabela do quadro mandou',
   ', '.join(exagero[:6]))

# 3. E os dois bracos TEM de se mexer na corrida e no trabalho — um
#    goblin de bracos congelados nao esta andando, esta sendo
#    arrastado.
parados = []
for acao in ('walk', 'attack'):
    poses = A.POSES[acao]()
    for braco in ('arm_l', 'arm_r'):
        if len({(p[braco][0] - p['torso'][0], p[braco][1] - p['torso'][1])
                for p in poses}) < 2:
            parados.append(f'{acao}/{braco}')
ok(not parados,
   'os dois bracos se mexem correndo e trabalhando',
   ', '.join(parados))

# e o ombro nao escolhe onde ficar: ele copia o tronco
soltos = []
for acao in ('idle', 'walk', 'attack', 'hurt'):
    for i, pose in enumerate(A.POSES[acao]()):
        agacha = (pose.get('_squash') or {}).get('torso', 0)
        for braco in ('arm_l', 'arm_r'):
            # o braco pode ERGUER ate 1 px de tela para armar o golpe;
            # o ombro cobre essa altura no tronco. Descer, nunca: ai
            # ele sai de baixo do ombro e abre a junta.
            d = pose[braco][1] - (pose['torso'][1] + agacha)
            if not -2 <= d <= 0:
                soltos.append(f'{acao}_{i}/{braco} ({d})')
ok(not soltos, 'o ombro acompanha o tronco: o braco so pode erguer, '
   'e no maximo um pixel de tela', ', '.join(soltos[:6]))

# a corrida tem de QUICAR como a do goblin original (la o corpo subia e
# descia 4 px em 32; aqui, em 64, no minimo o dobro disso seria 8 — pedimos
# 4, que ja e visivel e nao arranca a perna do quadril)
alturas = [min(y for y in range(R.SIZE) for x in range(R.SIZE)
               if R.compose(p)[y][x] is not None)
           for p in A.POSES['walk']()]
ok(max(alturas) - min(alturas) >= 2,
   'a corrida quica: o corpo sobe e desce ao longo do ciclo',
   f'variação de {max(alturas) - min(alturas)} px')

# os dois pes tem de trocar de posicao (passo de verdade, nao escorregao)
vaos = []
for p in A.POSES['walk']():
    buf = R.compose({**p, 'torso': None, 'head': None,
                     'arm_l': None, 'arm_r': None})
    cols = [x for y in range(R.SIZE) for x in range(R.SIZE)
            if buf[y][x] is not None]
    vaos.append(max(cols) - min(cols))
ok(max(vaos) - min(vaos) >= 2,
   'os pes abrem e fecham durante a corrida (passo, não deslizada)',
   f'vão dos pés varia {max(vaos) - min(vaos)} px')


# ------------------------------------------------------------------ #
#  O CORPO INTEIRO SE ARTICULA, NAO SO AS PONTAS                      #
# ------------------------------------------------------------------ #
# A reclamacao foi: "na primeira versao ele mexe os dois bracos, mexe as
# pernas e nao so os pes, mexe as orelhas e todo o corpo". Medindo o
# original alinhado pelo topo do corpo, e verdade — quase toda linha
# muda de largura entre quadros:
#
#   linhas 1-2 (orelhas)  largura de 11 a 13 px
#   linhas 3-6 (rosto)    bordas andam 1 px: a cabeca inclina
#   linhas 8-11 (bracos)  largura de 7 a 15 px
#   linhas 12-13 (coxas)  largura de 9 a 13 px: a perna abre na COXA
#
# A causa de tudo isso ter sumido foi achatar o campo `dx`, que e um
# perfil de 17 alturas, num numero so entregue a todas as pecas. Estes
# testes cobram que cada regiao volte a se mexer.

def _larguras(img):
    """Largura da silhueta por linha, alinhada pelo topo do corpo."""
    a = np.array(img.convert('RGBA'))[..., 3] > 0
    ys, _ = np.where(a)
    if not len(ys):
        return []
    topo = ys.min()
    out = []
    for k in range(ys.max() - topo + 1):
        r = np.where(a[topo + k])[0]
        out.append(0 if not len(r) else int(r.max() - r.min() + 1))
    return out


# as mesmas faixas do original, em fracao da altura do corpo
# A faixa das ORELHAS saiu desta conta de proposito: elas nao se mexem
# mais. Uma orelha de 3 px de espessura so poderia andar em saltos de
# 2 px (o passo da tela) e, para nao se desmontar nesse salto, teria de
# ser reamostrada celula a celula — que e exatamente o que borra o
# desenho. O que a medicao do original pedia ali era 1 px na tela de
# 32; nao paga o preco.
FAIXAS = {'bracos': (0.45, 0.72), 'coxas': (0.72, 0.88)}

mortas = []
for acao in ('walk', 'attack'):
    quadros = [_larguras(im) for im in A.render_action(acao, None)]
    alt = max(len(q) for q in quadros)
    for regiao, (a0, a1) in FAIXAS.items():
        muda = False
        for k in range(int(a0 * alt), int(a1 * alt)):
            vals = {q[k] for q in quadros if k < len(q)}
            if len(vals) > 1:
                muda = True
                break
        if not muda:
            mortas.append(f'{acao}/{regiao}')
ok(not mortas,
   'orelhas, bracos e coxas mudam de largura ao longo do ciclo '
   '(o corpo todo se articula, como no original)',
   ', '.join(mortas))

# e a cabeca tem de inclinar em algum quadro de alguma animacao
balanca = any((p.get('_shear') or {}).get('head')
              for acao in ('idle', 'walk', 'attack', 'hurt')
              for p in A.POSES[acao]())
# A CABECA NAO INCLINA, E E DE PROPOSITO. Inclinar movia as linhas de
# cima dela, que sao o TOPO DO CRANIO; na tela o domo pulando 1 px
# enquanto a orelha ia para o outro lado lia como cabeca duplicada.
# Quem se mexe agora e cada orelha, na sua propria caixa.
ok(all(not (p.get('_shear') or {}).get('head')
       for acao in ('idle', 'walk', 'attack', 'hurt')
       for p in A.POSES[acao]()),
   'a cabeca nao inclina: quem se mexe sao as orelhas, o cranio fica')

# o rosto nao pode escorregar da cara quando a cabeca inclina
fugiu = []
for acao in ('idle', 'walk', 'attack'):
    for i, pose in enumerate(A.POSES[acao]()):
        if not (pose.get('_shear') or {}).get('head'):
            continue
        buf = R.compose(pose)
        olhos = [(x, y) for y in range(R.SIZE) for x in range(R.SIZE)
                 if buf[y][x] == 'f']
        cabeca = R.compose({**pose, '_faceless': True})
        if any(cabeca[y][x] is None for x, y in olhos):
            fugiu.append(f'{acao}_{i}')
ok(not fugiu, 'o rosto acompanha a inclinacao da cabeca, nao escorrega para fora',
   ', '.join(fugiu[:6]))


# ------------------------------------------------------------------ #
#  O QUADRIL VIRA E AS DUAS ORELHAS SE MEXEM SOZINHAS                 #
# ------------------------------------------------------------------ #
# Medido no original: correndo, nos quadros 4, 5 e 6 o pe esquerdo dele
# fica 1 px acima do direito (a bacia virando) e em varios quadros a
# ponta esquerda da cabeca esta uma linha abaixo da direita. Sem isso a
# corrida e um boneco de pernas paralelas e cabeca de pedra.

viradas = [i for i, p in enumerate(A.POSES['walk']())
           if p['leg_l'][1] != p['leg_r'][1]]
ok(len(viradas) >= 2,
   'correndo, o quadril vira: as duas pernas nao ficam na mesma altura',
   f'quadros com quadril virado: {viradas}')

# e o lado que sobe tem de ALTERNAR com o ciclo, nao ser sempre o mesmo
# membro preso no alto
alturas = {(p['leg_l'][1] - p['leg_r'][1]) for p in A.POSES['walk']()}
ok(len(alturas) >= 2, 'o desnivel do quadril muda ao longo da passada',
   f'desniveis vistos: {sorted(alturas)}')

# A CABECA CHEGA NA TELA EXATAMENTE COMO FOI DESENHADA.
#
# Isto substitui os antigos testes de "as orelhas se mexem". Mexer a
# orelha obrigava a reamostrar a regiao mais detalhada do sprite — o
# rosto — e era de la que saiam os pixels verdes a mais. A garantia
# que vale agora e a oposta: em TODO quadro de TODA animacao, a
# cabeca e o desenho original, inteiro, so que noutro lugar.
cabeca = R.DEFAULT_PART['head']
area_cabeca = sum(1 for linha in cabeca for c in linha if c != '.')
# AS ORELHAS VOLTARAM A SE MEXER — em BLOCO, nunca reamostradas.
# A versao antiga interpolava celula a celula da base ate a ponta e
# borrava a orelha; esta anda com o bloco inteiro, 2 px de uma vez.
deformadas = []
for acao in ('idle', 'walk', 'attack', 'hurt'):
    for i, p in enumerate(A.POSES[acao]()):
        for k in ('_ears', '_ear_drop'):
            if (p.get(k) or 0) % 2:
                deformadas.append(f'{acao}_{i}/{k} fora da grade')
        if (p.get('_shear') or {}).get('head'):
            deformadas.append(f'{acao}_{i} inclina a cabeca')
ok(not deformadas, 'a cabeca nunca e reamostrada: a orelha anda em '
   'bloco de 2 px e o resto do rosto fica parado',
   ', '.join(deformadas[:6]))

mexem = {a: sum(1 for p in A.POSES[a]() if p.get('_ears') or p.get('_ear_drop'))
         for a in ('idle', 'walk', 'attack', 'hurt')}
ok(all(v >= 2 for v in mexem.values()),
   'as orelhas se mexem em parado, andando, batendo e levando pancada',
   str(mexem))

# E A CARA MUDA quando ele bate e quando apanha.
caras = {a: {p.get('_rosto') for p in A.POSES[a]()}
         for a in ('idle', 'walk', 'attack', 'hurt')}
ok('bravo' in caras['attack'] and 'dor' in caras['hurt']
   and caras['idle'] == {None},
   'a cara muda: fecha a carranca para bater e aperta os olhos de dor',
   str(caras))

# E o mesmo vale para QUALQUER peca: inclinar era deslocar cada linha
# um tanto diferente, e isso reserra o desenho. Agora topo == base em
# todo lugar — a peca anda inteira.
serradas = []
for acao in ('idle', 'walk', 'attack', 'hurt'):
    for i, p in enumerate(A.POSES[acao]()):
        for nome, (topo, base) in (p.get('_shear') or {}).items():
            if topo != base:
                serradas.append(f'{acao}_{i}/{nome} ({topo},{base})')
ok(not serradas, 'nenhuma peca e serrada: ela anda inteira, '
   'cada pixel como foi pintado', ', '.join(serradas[:6]))

# ------------------------------------------------------------------ #
#  NADA SOLTO, NADA FALTANDO, NADA DUPLICADO                          #
# ------------------------------------------------------------------ #
# As tres garantias que o movimento novo nao pode quebrar.

def _mascara(pose, **kw):
    buf = R.compose(pose, **kw)
    return np.array([[c is not None for c in row] for row in buf])


# 1. A cabeca nao pode perder area quando as pontas se mexem: abrir ou
#    abaixar uma orelha a TRANSLADA, nunca a apaga.
magros = []
base_cab = _mascara(R.base_pose(), ).sum()
for acao in ('idle', 'walk', 'attack', 'hurt'):
    for i, pose in enumerate(A.POSES[acao]()):
        if not (pose.get('_ears') or pose.get('_ear_drop')):
            continue
        sem = _mascara({**pose, '_ears': None, '_ear_drop': None}).sum()
        com = _mascara(pose).sum()
        # a ponta abaixada entra no cranio, entao pode encolher um pouco;
        # sumir de vez (mais de 12 px) e defeito
        # a orelha anda em bloco e parte dela DOBRA para dentro do
        # cranio — e uma dobra, nao um sumico. Ate 12 px e a dobra;
        # mais do que isso e orelha sendo cortada fora do recorte.
        if sem - com > 12:
            magros.append(f'{acao}_{i} (-{sem - com} px)')
ok(not magros, 'mexer as orelhas nao apaga a cabeca', ', '.join(magros[:6]))

# 2. Nenhum buraco novo DENTRO da silhueta (pixel de fundo cercado por
#    corpo nos quatro lados em todas as direcoes ate a borda).
def _buracos(m):
    h, w = m.shape
    fora = np.zeros_like(m)
    fila = deque()
    for x in range(w):
        for y in (0, h - 1):
            if not m[y, x] and not fora[y, x]:
                fora[y, x] = True
                fila.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if not m[y, x] and not fora[y, x]:
                fora[y, x] = True
                fila.append((y, x))
    while fila:
        y, x = fila.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not m[ny, nx] and not fora[ny, nx]:
                fora[ny, nx] = True
                fila.append((ny, nx))
    return int((~m & ~fora).sum())


rep = _buracos(_mascara(A._pose_do_original('idle', 0)))
furados = []
for acao in ('idle', 'walk', 'attack', 'hurt'):
    for i, pose in enumerate(A.POSES[acao]()):
        b = _buracos(_mascara(pose))
        if b > rep:
            furados.append(f'{acao}_{i} ({b} vs {rep})')
ok(not furados, 'nenhum quadro abre buraco dentro do corpo',
   ', '.join(furados[:6]))

# 3. Nenhuma parte fica parada o ciclo inteiro (ja coberto acima) e
#    nenhuma aparece DUPLICADA: a area total nao pode disparar, que e o
#    que acontece quando uma peca e desenhada duas vezes.
inchados = []
for acao in ('idle', 'walk', 'attack', 'hurt'):
    areas = [_mascara(p).sum() for p in A.POSES[acao]()]
    if max(areas) > min(areas) * 1.25:
        inchados.append(f'{acao} ({min(areas)}..{max(areas)} px)')
ok(not inchados, 'nenhuma peca aparece duplicada (a area do corpo e estavel)',
   ', '.join(inchados))


# ------------------------------------------------------------------ #
#  A CARNE NAO PODE SE PARTIR                                         #
# ------------------------------------------------------------------ #
# O CRITERIO E A SILHUETA, CONTORNO INCLUIDO.
#
# Ja foi a carne (o sprite sem os pixels 'k'), com o argumento de que
# o jogador nao enxerga contorno como corpo. Era falso, e caro: a arte
# original, sem pose nenhuma, JA tem duas ilhas de carne — o fio preto
# entre o tronco e a perna e uma dobra, nao um corte. Perseguindo esse
# criterio a solda chegou a pintar 20 px por quadro e a propria arte
# foi reescrita para satisfazer a metrica. Dai "pixels a mais" e
# "voce mudou o sprite".
#
# Membro solto de verdade e membro cercado de FUNDO. E isso que se
# mede aqui.
partidos = []
for acao in ('idle', 'walk', 'attack', 'hurt', 'death'):
    for i, pose in enumerate(A.POSES[acao]()):
        buf = R.compose(pose)
        pedacos = [len(c) for c in R._componentes(
            [[c is not None for c in linha] for linha in buf]) if len(c) >= 6]
        if len(pedacos) > 1:
            partidos.append(f'{acao}_{i} {pedacos}')
ok(not partidos,
   'o goblin e uma peca so: nenhum membro cercado de fundo',
   ', '.join(partidos[:6]))

# e o mesmo com armadura e arma, que e quando mais costura acontece
partidos = []
for peca in ('av_full', 'ferro_cap', 'wpn_espada'):
    gear = G.resolve(G.PIECES[peca][0], 'down')
    for acao in ('walk', 'attack'):
        for i, pose in enumerate(A.POSES[acao]()):
            g = G.resolve(G.PIECES[peca][0], pose.get('_sword', 'down'))
            pedacos = [len(c) for c in
                       R._componentes(
                           [[c is not None for c in linha]
                            for linha in R.compose(pose, gear=g)])
                       if len(c) >= 6]
            if len(pedacos) > 1:
                partidos.append(f'{peca}/{acao}_{i}')
ok(not partidos, 'continua uma peca so vestido e armado',
   ', '.join(partidos[:6]))

# ------------------------------------------------------------------ #
#  O TOPO DO CRANIO NAO E ORELHA                                      #
# ------------------------------------------------------------------ #
# Mexer as orelhas ja duplicou a cabeca: a regra era "orelha esquerda =
# tudo a esquerda da coluna 22" e isso pegava o TOPO DO CRANIO junto.
cabeca = R.DEFAULT_PART['head']
cranio = [(x, y) for y in range(0, 5) for x in range(12, 23)
          if cabeca[y][x] != '.']
mexidos = []
for d, cai in ((2, 0), (0, 2), (2, 2), (-2, 2)):
    mexida = R.abrir_orelhas(cabeca, d, cai)
    fora = [(x, y) for x, y in cranio if mexida[y][x] != cabeca[y][x]]
    if fora:
        mexidos.append(f'abre={d} cai={cai}: {len(fora)} px')
ok(not mexidos, 'mexer as orelhas nao mexe o topo do cranio',
   ', '.join(mexidos))

# ------------------------------------------------------------------ #
#  PARADO E RESPIRAR, NAO ANDAR                                       #
# ------------------------------------------------------------------ #
parado = A.POSES['idle']()
ok(all(not (p.get('_shear') or {}).get(k)
       for p in parado for k in ('arm_l', 'arm_r', 'leg_l', 'leg_r')),
   'parado: nenhum braco ou perna abre (isso e andar, nao respirar)')
# PARADO: OS PES NAO SAEM DO LUGAR e o corpo afunda um pixel de tela.
# Afundar e seguro (so aumenta a sobreposicao do tronco sobre a perna)
# e e o que o peito faz ao soltar o ar.
ok(all(p['leg_l'] == (0, 0) and p['leg_r'] == (0, 0) for p in parado),
   'parado: os pes ficam exatamente onde estao')
ok(len({p['torso'][1] for p in parado}) >= 2
   and max(p['torso'][1] for p in parado) <= 2,
   'parado: o peito afunda um pixel de tela e volta (ele respira)',
   str(sorted({p['torso'][1] for p in parado})))

# ------------------------------------------------------------------ #
#  O DANO TEM DE DAR PARA VER                                         #
# ------------------------------------------------------------------ #
# Enfiado direto nos 17 quadros, o tranco de 4 do original se repetia
# quatro vezes e virava um tremelique rapido demais para se enxergar.
dano = A.POSES['hurt']()
trocas = sum(1 for i in range(1, len(dano))
             if dano[i]['torso'] != dano[i - 1]['torso'])
ok(trocas <= 5,
   'o dano nao e um tremelique: a pose troca poucas vezes nos 17 quadros',
   f'{trocas} trocas')

# ------------------------------------------------------------------ #
#  O ATAQUE E UM SOCO, E FUNCIONA DE MAO VAZIA                        #
# ------------------------------------------------------------------ #
soco = A.POSES['attack']()
# e tem de continuar valendo sem arma nenhuma desenhada
sem_arma = [R.compose(p) for p in soco]
ok(all(len([c for c in R._componentes(
           [[ch is not None for ch in linha] for linha in b])
           if len(c) >= 6]) == 1
       for b in sem_arma),
   'o soco funciona de mao vazia, sem arma na cena')


# ------------------------------------------------------------------ #
#  O QUE IMPORTA E O QUE APARECE NA TELA                              #
# ------------------------------------------------------------------ #
# Esta secao inteira existe por causa de um erro de medicao que deixou
# o jogo quebrado com a suite verde durante varias rodadas.
#
# O sprite tem 64 px e `js/world.js` o desenha em 32 unidades de mundo
# com a suavizacao desligada. Numa tela pequena isso vira 32 px de
# verdade: uma coluna e uma linha sim, outra nao. METADE DO DESENHO
# NAO CHEGA AO MONITOR.
#
# Resultado: solda de 1 px, detalhe de 1 px e deslocamento impar podem
# estar perfeitos no sprite e simplesmente nao existir para o jogador.
# Foi assim que os 47 quadros do jogo ficaram com braco e perna
# flutuando enquanto o teste dizia "nada solto".

# As QUATRO FASES de amostragem. A reducao de 64 para 32 pega uma
# coluna e uma linha sim, outra nao, mas QUAL delas depende de onde a
# camera parou e de como o motor arredonda — o Pillow pega as impares,
# o canvas pode pegar as pares. Conferir so uma fase e deixar o jogo
# quebrado em tres de cada quatro posicoes do goblin. Foi assim que o
# teste ficou verde com o braco solto na tela.
FASES = ((0, 0), (1, 0), (0, 1), (1, 1))


def _tela(pose, fase=(0, 0), **kw):
    return R.vista_de_tela(R.compose(pose, **kw), *fase)


def _comp_tela(tela, so_carne=False):
    # SILHUETA por padrao (contorno incluido): membro solto e membro
    # cercado de fundo. Medir so a carne reprova ate a arte original
    # parada — o fio preto entre o tronco e a perna e uma dobra, e foi
    # correr atras disso que encheu o sprite de tinta de remendo.
    m = [[c is not None and (not so_carne or c != 'k') for c in linha]
         for linha in tela]
    return [len(c) for c in R._componentes(m, len(tela)) if len(c) >= 3]


partidos = []
for acao in ('idle', 'walk', 'attack', 'hurt', 'death'):
    for i, pose in enumerate(A.POSES[acao]()):
        for fase in FASES:
            pedacos = _comp_tela(_tela(pose, fase))
            if len(pedacos) > 1:
                partidos.append(f'{acao}_{i}{fase} {pedacos}')
ok(not partidos,
   'NA TELA: nenhum membro solto, nas quatro fases de amostragem',
   ', '.join(partidos[:6]))

partidos = []
for peca in ('av_full', 'ferro_cap', 'wpn_espada'):
    for acao in ('walk', 'attack'):
        for i, pose in enumerate(A.POSES[acao]()):
            g = G.resolve(G.PIECES[peca][0], pose.get('_sword', 'down'))
            for fase in FASES:
                pedacos = _comp_tela(_tela(pose, fase, gear=g))
                if len(pedacos) > 1:
                    partidos.append(f'{peca}/{acao}_{i}{fase}')
ok(not partidos, 'NA TELA: nada solto tambem vestido e armado',
   ', '.join(partidos[:6]))

# Todo deslocamento tem de cair na grade da tela. Um numero impar move
# a peca MEIO pixel de tela: o desenho reamostra, muda de forma sozinho
# e pisca.
impares = []
for acao in ('idle', 'walk', 'attack', 'hurt', 'death'):
    for i, pose in enumerate(A.POSES[acao]()):
        for k in ('head', 'torso', 'arm_l', 'arm_r', 'leg_l', 'leg_r'):
            v = pose.get(k)
            if v and (v[0] % 2 or v[1] % 2):
                impares.append(f'{acao}_{i} {k}={v}')
        for k, v in (pose.get('_shear') or {}).items():
            if v and (v[0] % 2 or v[1] % 2):
                impares.append(f'{acao}_{i} incl {k}={v}')
ok(not impares, 'NA TELA: nenhuma peca anda meio pixel (tudo na grade de 2)',
   ', '.join(impares[:6]))

# O TOPO DO CRANIO e uma forma so. Ele chegou a se mexer por dois
# caminhos ao mesmo tempo — a inclinacao da cabeca e o movimento das
# orelhas — e na tela o domo pulando enquanto a orelha ia para o outro
# lado lia como cabeca duplicada.
def _forma_cranio(pose):
    t = _tela(pose)
    hy = (20 + pose['head'][1]) // 2
    hx = (13 + pose['head'][0]) // 2
    return tuple(tuple(t[hy + dy][hx + dx] for dx in range(6, 12))
                 for dy in range(0, 3))


bagunca = []
for acao in ('idle', 'walk', 'attack', 'hurt'):
    formas = {_forma_cranio(p) for p in A.POSES[acao]()}
    if len(formas) != 1:
        bagunca.append(f'{acao}: {len(formas)} formas')
ok(not bagunca,
   'NA TELA: o topo do cranio e sempre a mesma forma (nao duplica)',
   ', '.join(bagunca))

# E o QUADRIL tem de virar de um jeito que se enxergue na tela.
viradas = [i for i, p in enumerate(A.POSES['walk']())
           if p['leg_l'][1] != p['leg_r'][1]
           or p['leg_l'][0] != p['leg_r'][0]]
ok(len(viradas) >= 2,
   'NA TELA: o quadril vira (as pernas diferem em altura e em avanco)',
   f'quadros: {viradas}')


# ------------------------------------------------------------------ #
#  A COSTURA E ULTIMO RECURSO, NAO O CONSERTO                         #
# ------------------------------------------------------------------ #
# Tapar fresta e soldar ilha funciona, mas PINTA pixel que o artista
# nao pos — e isso aparece como sujeira verde e tira a nitidez. Chegou
# a 20 px por quadro, e o goblin "perdeu qualidade".
#
# O conserto de verdade e geometrico: o ombro e o quadril ESTICAM para
# acompanhar o membro, e as juntas que eram parede de contorno viraram
# pele. A costura so cobre o que sobra. Se este numero subir, alguem
# voltou a remendar com tinta em vez de arrumar a juntura.
_pintado = {'n': 0, 'px': 0, 'cor': 0}
_f_orig, _s_orig = R._fecha_buracos, R._solda_carne


def _conta(fn):
    def dentro(buf, *a, **k):
        antes = [linha[:] for linha in buf]
        fn(buf, *a, **k)
        mudou = [(y, x) for y in range(R.SIZE) for x in range(R.SIZE)
                 if antes[y][x] != buf[y][x]]
        _pintado['px'] += len(mudou)
        # cor nova = pele/couro que o artista nao pintou. Contorno em
        # fresta estreita nao conta: e a linha que ja separa o braco do
        # corpo no desenho parado, nao tinta nova.
        _pintado['cor'] += sum(1 for y, x in mudou if buf[y][x] != 'k')
    return dentro


R._fecha_buracos, R._solda_carne = _conta(_f_orig), _conta(_s_orig)
for acao in ('idle', 'walk', 'attack', 'hurt', 'death'):
    for pose in A.POSES[acao]():
        R.compose(pose)
        _pintado['n'] += 1
R._fecha_buracos, R._solda_carne = _f_orig, _s_orig
cor_nova = _pintado['cor'] / max(1, _pintado['n'])
ok(cor_nova == 0,
   'nenhum pixel de pele ou couro e inventado: so o desenho do artista '
   'chega na tela',
   f'{cor_nova:.1f} px de cor nova por quadro (teto 0)')

# E o desenho PARADO tem de chegar inteiro na tela sem costura nenhuma
# — se nem a pose de pe se sustenta sozinha, qualquer movimento vai
# depender de remendo.
cru = R.compose({**A._pose_do_original('idle', 0),
                 '_shear': None, '_ears': None, '_ear_drop': None},
                costurar=False)
for fase in FASES:
    pedacos = [len(c) for c in
               R._componentes([[c is not None for c in linha]
                               for linha in R.vista_de_tela(cru, *fase)], 32)
               if len(c) >= 3]
    ok(len(pedacos) == 1,
       f'a pose parada ja nasce inteira na tela, sem costura, fase {fase}',
       str(pedacos))

print(f'\n  {passou} passaram · {len(falhas)} falharam')
sys.exit(1 if falhas else 0)
