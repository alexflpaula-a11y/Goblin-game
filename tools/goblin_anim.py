#!/usr/bin/env python3
"""
Animacoes do goblin v2.

Cada animacao e uma lista de poses geradas a partir do rig de
`goblin_rig.py`. A contagem de quadros e exatamente a que o jogo ja usa:

    idle 5 | walk 8 | attack 17 | hurt 17 | death 12   (59 no total)

Nenhum quadro e desenhado a mao, e nenhum movimento e inventado: correr,
parar, atacar e levar dano sao o movimento do PRIMEIRO goblin (o de
32 px), medido quadro a quadro pelo tools/orig_captura.py e aplicado a
estas pecas. A morte e a unica que e nossa, porque o jogo mudou: ela e
instantanea, com o GOBLINZED vermelho.
"""

import json
import math
import os

from PIL import Image

import goblin_rig as R

FRAME_COUNTS = {'idle': 5, 'walk': 8, 'attack': 17, 'hurt': 17, 'death': 12}

# Maior passo que uma parte pode dar entre dois quadros. Nao e um numero
# de gosto: e o maior passo que o PROPRIO goblin original da, dobrado
# para a nossa escala. O tremor do dano e o quique da corrida sao bruscos
# no original de proposito, e alisar isso seria deixar de copiar o
# movimento dele — que e justamente o que se pediu.
# Maior salto que uma peca pode dar de um quadro para o vizinho.
# Medido no original: correndo, o pe dele sobe 3 px de uma vez entre os
# quadros 3 e 4 (a passada com o quadril virado), e 3 na tela de 32 sao
# 6 aqui. Limitar a 4, como estava, proibia a propria passada do goblin
# que estamos copiando.
SOBE_MAX = 2       # teto do sobe-e-desce do corpo, em px do sprite
MAX_STEP = 6


def _arred(v):
    """Arredonda meio para cima (o round() do Python arredonda para par)."""
    return int(math.floor(v + 0.5))


ACTIONS = ('idle', 'walk', 'attack', 'hurt', 'death')


def _pose(body=(0, 0), head=(0, 0), arm_l=(0, 0), arm_r=(0, 0),
          leg_l=(0, 0), leg_r=(0, 0), sword=None, kind='diag', squash=0,
          shear=None):
    """Monta a pose somando o deslocamento global `body` a cada parte.

    `sword` nao e uma parte do corpo: e a ANCORA da mao que segura a arma.
    Por padrao ela acompanha o braco da arma — se cada animacao repetisse o
    valor na mao, bastaria esquecer de atualizar um deles para a arma
    equipada flutuar longe do punho (ja aconteceu na animacao de morte).

    `shear` e a articulacao: {'leg_l': (dx_no_quadril, dx_no_pe), ...}. E
    por ela que os membros se MEXEM. Ver a regra de ouro abaixo.
    """
    if sword is None:
        sword = arm_l
    bx, by = body
    # AGACHAR SEM ESPREMER.
    #
    # Antes o agachamento apagava 2 linhas do meio do tronco
    # (goblin_rig.squash_rows). Apagar linha e perder desenho: a barra
    # da tunica sumia e voltava duas vezes por golpe, e e esse tipo de
    # coisa que faz o sprite parecer de qualidade pior. Agora cabeca,
    # bracos e tronco descem `squash` px inteiros e os pes ficam
    # plantados — o goblin dobra os joelhos sem que um unico pixel
    # mude de forma.
    if squash:
        head = (head[0], head[1] + squash)
        arm_l = (arm_l[0], arm_l[1] + squash)
        arm_r = (arm_r[0], arm_r[1] + squash)
        sword = (sword[0], sword[1] + squash)
        by += squash
        # as pernas sao escritas em relacao ao corpo: desconta, senao
        # elas descem junto e o goblin afunda no chao
        leg_l = (leg_l[0], leg_l[1] - squash)
        leg_r = (leg_r[0], leg_r[1] - squash)
        squash = 0
    # Na referencia a adaga esta na mao DIREITA (lado direito do espectador),
    # entao `arm_l` das tabelas de animacao e o braco da arma -> parte arm_r.
    return {
        'head':  (head[0] + bx, head[1] + by),
        'torso': (bx, by),
        'arm_r': (arm_l[0] + bx, arm_l[1] + by),
        'arm_l': (arm_r[0] + bx, arm_r[1] + by),
        'leg_l': (leg_l[0] + bx, leg_l[1] + by),
        'leg_r': (leg_r[0] + bx, leg_r[1] + by),
        'sword': (sword[0] + bx, sword[1] + by),
        '_sword': kind,
        # ORELHAS PARADAS, DE PROPOSITO.
        #
        # Elas ja se mexeram aqui, e foi um dos focos de "pixels a
        # mais". A orelha tem 3 px de espessura e tudo neste rig anda
        # de 2 em 2 px (um pixel de tela): uma orelha de 3 px dando um
        # salto de 2 nao balanca, ela se desmonta — e para ela nao se
        # desmontar era preciso reamostrar celula por celula, que e
        # justamente o que borra o desenho. No original a variacao
        # medida e de 1 px na tela de 32; nao vale o preco.
        '_ears': None,
        '_ear_drop': None,
        # quanto o tronco comprime neste quadro (agachar); ver
        # goblin_rig.squash_rows
        '_squash': {'torso': squash} if squash else None,
        '_shear': shear or None,
    }


# ===================================================================== #
#  AS ANIMACOES SAO AS DO PRIMEIRO GOBLIN                               #
# ===================================================================== #
# Nada aqui e invencao. Correr, parar, atacar e levar dano sao o
# movimento do goblin original de 32 px, medido quadro a quadro pelo
# tools/orig_captura.py e aplicado ao rig novo. Os desenhos sao outros —
# nao da para copiar pixel — mas o movimento e o mesmo.
#
# O que o original faz, em numero (ver tools/orig_movimento.json):
#
#   parado   o corpo cresce 2 px e volta; o pe nao sai do chao
#   correr   o corpo QUICA: o topo sobe 3 px e a base sobe 4, ou seja
#            ele chega a tirar os dois pes do chao. De lado quase nao
#            anda — o centro varia 1,3 px no ciclo inteiro
#   atacar   um golpe de 4 quadros repetido quatro vezes: pose, investida
#            (os DOIS bracos abrem, as pernas afastam 4 px), recuo, pose
#   dano     tremor: o corpo afunda 1 px, salta 2 e as pernas abrem
#
# Repare no que o original NAO faz: o corpo nao escorrega de lado e o
# braco nao sai passeando longe do ombro. O que se mexe muito e a
# vertical e a PONTA dos membros. Era por tentar balancar o braco inteiro
# que ele vivia parecendo solto.

# ------------------------------------------------------------------- #
#  COMO O MOVIMENTO MEDIDO VIRA POSE                                    #
# ------------------------------------------------------------------- #
# O orig_captura.py entrega, para cada quadro, duas funcoes continuas da
# ALTURA do corpo: quanto aquela altura andou de lado (dx) e quanto subiu
# ou desceu (dy). Cada peca do rig le essas funcoes na linha em que
# encosta nas outras.
#
# E daqui que sai a garantia que faltava: o ombro le o campo na MESMA
# linha em que o tronco o le, entao os dois caem no mesmo lugar por
# construcao. Nao existe numero, tabela ou amplitude que possa separar um
# do outro — e o mesmo valor, lido da mesma funcao. O braco nao tem como
# soltar.
#
# O que cada peca faz de proprio e so ESTICAR a ponta: a mao e o pe
# viajam por inclinacao, com o ombro e o quadril parados onde o campo
# mandou. O quanto eles esticam tambem foi medido no original.

CAMPO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     'orig_movimento.json')
with open(CAMPO) as _f:
    MOVIMENTO = json.load(_f)

# O goblin velho cabia numa tela de 32 e o novo cabe numa de 64, entao
# tudo que foi medido vale em dobro. (Na pratica o movimento fica ate
# mais discreto que no original: o corpo dele tinha 15 linhas e o nosso
# tem 44, ou seja o mesmo pulo de 4 px era 27% da altura dele e e 18% da
# nossa.)
ESCALA = 2.0

# Onde o corpo comeca e termina, em linhas da tela de 64. E a faixa que
# corresponde ao corpo inteiro do original.
CORPO_TOPO = 20
CORPO_BASE = 63

# Em que linha cada peca encosta nas outras e ate onde ela vai.
# (ombro/quadril, ponta)
ENCAIXE = {
    'head':  (30, 30),     # a cabeca nao inclina: le o campo no meio
    'torso': (40, 60),
    'arm_l': (41, 54),     # braco da esquerda da tela
    'arm_r': (43, 54),     # braco da direita da tela, o que segura a arma
    'leg_l': (57, 63),
    'leg_r': (57, 63),
}

# Qual medida do original estica a ponta de cada peca.
# De que lado do corpo esta cada membro, para ele ler a metade certa do
# campo `meia`.
LADO = {'arm_l': 'esq', 'arm_r': 'dir', 'leg_l': 'esq', 'leg_r': 'dir'}

# Em que FRACAO da altura do corpo esta a ponta de cada membro NO
# ORIGINAL — medido nos quadros dele: a mao fica entre as linhas 7 e 9
# de 15 (uns 60%) e o pe na ultima. Nao da para usar o pixel da ponta do
# nosso goblin: ele e mais comprido de braco, a mao dele cai em 79%, e
# la o original ja esta na coxa.
FRACAO_PONTA = {'arm_l': 0.60, 'arm_r': 0.60, 'leg_l': 1.0, 'leg_r': 1.0}

PONTA = {
    'arm_l': 'braco_esq', 'arm_r': 'braco_dir',
    'leg_l': 'pe_esq', 'leg_r': 'pe_dir',
}

# Quanto a ponta pode viajar — e para que LADO.
#
# Aqui esta a correcao do braco que vivia parecendo solto. Nao era o
# braco se separando do corpo: medindo quadro a quadro, no repouso a
# fresta entre o braco e o tronco e de ZERO pixel, e durante a animacao
# ela abria ate QUATRO. Encostar num canto nao basta — o olho ve o buraco
# de fundo preto ao longo do braco inteiro e le "solto".
#
# A razao e o desenho base, que nao da para mudar: o braco pende ao LADO
# do tronco, com contorno proprio, e nao por cima dele. Entao cada pixel
# que a mao vai para FORA vira buraco; para DENTRO, nao, porque o tronco
# cobre. O limite e assimetrico por causa disso:
#
#   para dentro   3 px (o tronco cobre, nao abre nada)
#   para fora     0 px (qualquer pixel para fora e buraco)
#
# A perna corre por BAIXO do tronco e nao tem esse problema: pode abrir
# para os dois lados. E por isso que a passada e a investida continuam
# largas mesmo com o braco contido — que, de resto, e como o original se
# comporta: la o braco quase nao sai do lugar, quem abre sao as pernas.
#
# 'fora' diz para que lado fica o lado de fora de cada braco, visto da
# tela: o braco da esquerda abre para x menor, o da direita para x maior.
# Quanto o alto do cranio (e com ele as ORELHAS) pode balancar em
# relacao ao queixo. Duas casas da grade da tela: mais que isso e a
# cabeca parece desencaixar do pescoco.
BALANCO_CABECA = 2

# Quanto as pernas podem andar de lado em relacao ao tronco (o goblin
# trocando o peso de pe). Uma casa da grade da tela.
DESLOCA_PESO = 2

# Quanto o lado girado do quadril avanca. Uma casa da grade da tela: o
# desnivel medido no original e de 1 px de tela e sozinho nao se ve.
QUADRIL_GIRO = 2

ESTICA = {
    # Quanto cada membro pode escorregar, em pixels do sprite (2 = um
    # pixel de tela). O teto nao e estetico, e geometrico: o braco
    # sobrepoe o tronco em 7 px e a perna em 9, e o membro anda
    # INTEIRO. Passando de 4 o ombro comeca a sair de cima do tronco e
    # a junta aparece — era quando entrava a tinta de remendo.
    #
    # 4 px aqui sao 2 pixels de tela: no tamanho em que o jogo desenha,
    # e um balanco de braco bem visivel.
    'arm_l': {'dentro': 4, 'fora': 4, 'sinal_fora': -1},
    'arm_r': {'dentro': 4, 'fora': 4, 'sinal_fora': +1},
    'leg_l': {'dentro': 4, 'fora': 4, 'sinal_fora': -1},
    'leg_r': {'dentro': 4, 'fora': 4, 'sinal_fora': +1},
}


def _amostra(valores, u):
    """Le o campo na altura u (0 no topo da cabeca, 1 no chao)."""
    u = max(0.0, min(1.0, u))
    pos = u * (len(valores) - 1)
    k = int(pos)
    if k >= len(valores) - 1:
        return valores[-1]
    t = pos - k
    return valores[k] * (1 - t) + valores[k + 1] * t


def _campo(acao, i):
    """Devolve (dx, dy): quanto a linha `y` da tela andou neste quadro."""
    q = MOVIMENTO['acoes'][acao][i]
    vao = CORPO_BASE - CORPO_TOPO

    def dx(y):
        return _amostra(q['dx'], (y - CORPO_TOPO) / vao) * ESCALA

    def dy(y):
        return _amostra(q['dy'], (y - CORPO_TOPO) / vao) * ESCALA

    def meia(lado, fracao):
        """Quanto o lado `lado` abriu NAQUELA FRACAO da altura do corpo.

        Fracao, nao pixel: os dois goblins nao tem a mesma proporcao. A
        mao do nosso chega a 79%% da altura dele e a do original para em
        60%% — ler o campo no pixel do nosso faz o braco copiar o que a
        COXA do original fez (e no ataque isso dava zero).
        """
        campo = q.get('meia', {}).get(lado)
        if not campo:
            return 0.0
        return _amostra(campo, fracao) * ESCALA

    return dx, dy, q['alcance'], meia


FASES_TELA = ((0, 0), (1, 0), (0, 1), (1, 1))


def _inteiro_na_tela(pose):
    """O corpo fica em UMA peca so na tela, sem precisar costurar nada?

    Olha a carne (sem o contorno, que o jogador nao le como corpo) nas
    quatro fases de amostragem da reducao para 32.
    """
    buf = R.compose(pose, costurar=False)
    for fx, fy in FASES_TELA:
        tela = R.vista_de_tela(buf, fx, fy)
        carne = [[c is not None and c != 'k' for c in linha]
                 for linha in tela]
        grandes = [c for c in R._componentes(carne, len(tela))
                   if len(c) >= 3]
        if len(grandes) > 1:
            return False
    return True


def _ilhas(pose):
    """Quantos pedacos de carne soltos o quadro tem, somando as fases."""
    buf = R.compose(pose, costurar=False)
    total = 0
    for fx, fy in FASES_TELA:
        tela = R.vista_de_tela(buf, fx, fy)
        carne = [[c is not None and c != 'k' for c in linha]
                 for linha in tela]
        total += max(0, len([c for c in R._componentes(carne, len(tela))
                             if len(c) >= 3]) - 1)
    return total


def _encaixar(pose, inclina):
    """Recolhe o que nao encosta, ate o corpo ficar inteiro na tela.

    A costura do rig (tapar fresta, soldar ilha) salva o quadro, mas ela
    PINTA — chegou a acrescentar 20 px por quadro, e isso aparece como
    sujeira verde e tira a nitidez do desenho. E melhor um membro
    esticar 2 px menos do que o desenho ganhar pixel que nao e do
    artista.

    Cada volta experimenta recolher UM movimento de cada vez e fica com
    o que mais fecha o corpo. Mexer no primeiro candidato da lista nao
    serve: numa versao anterior um descolamento da ORELHA fazia o laco
    ir zerando as inclinacoes dos bracos, uma por uma, ate a corrida
    ficar sem balanco nenhum — consertava a parte errada.
    """
    ruim = _ilhas(pose)
    for _ in range(6):
        if not ruim:
            return pose
        melhor = None
        for alvo in ('arm_l', 'arm_r', 'leg_l', 'leg_r', '_ears',
                     '_ear_drop'):
            tentativa = dict(pose)
            if alvo in ('_ears', '_ear_drop'):
                if not pose.get(alvo):
                    continue
                tentativa[alvo] = None
            else:
                if not inclina.get(alvo):
                    continue
                topo, base = inclina[alvo]
                novo = base - 2 if base > 0 else base + 2
                novo_incl = dict(inclina)
                if abs(novo) < 2:
                    novo_incl.pop(alvo)
                else:
                    novo_incl[alvo] = (R.na_grade(novo / 2), novo)
                tentativa['_shear'] = novo_incl or None
            nota = _ilhas(tentativa)
            if nota < ruim and (melhor is None or nota < melhor[0]):
                melhor = (nota, alvo, tentativa)
        if melhor is None:
            return pose
        ruim, _alvo, pose = melhor
        if pose.get('_shear') is not None:
            inclina.clear()
            inclina.update(pose['_shear'])
        elif '_shear' in pose:
            inclina.clear()
    return pose


def _pose_do_original(acao, i, squash=0, kind='diag', respira=False):
    """Monta a pose do quadro `i` de `acao` a partir do goblin original."""
    dx, dy, alcance, meia = _campo(acao, i)

    # Tudo aqui cai na grade da tela (de dois em dois). Ver a explicacao
    # em goblin_rig.PASSO_TELA: o jogo mostra este sprite de 64 numa
    # caixa de 32, entao um deslocamento IMPAR nao move o goblin — ele
    # reserra o desenho inteiro, e e isso que se ve como "estranho".
    # ALTURA DO TRONCO, COM TETO.
    #
    # O campo dy vem do goblin original, que e um sprite de 32, e aqui
    # ele e multiplicado por 2 para virar sprite de 64. Na corrida isso
    # dava ate 8 px de subida — QUATRO pixels de tela. O goblin nao
    # andava, ele saltitava no ar, e e disso que vinha a sensacao de
    # "estranho": sem contato com o chao, a passada nao le como passada.
    #
    # Andar e o corpo subir UM pixel de tela no apoio e voltar. O
    # degrau de 2 px e o minimo que a tela enxerga e o maximo que uma
    # caminhada aguenta; quem mostra o passo e a perna, nao o corpo
    # inteiro decolando.
    ty = max(-SOBE_MAX, min(SOBE_MAX, R.na_grade(dy(50))))
    # bacia girando: desnivel entre os dois pes, medido no original
    quadril = R.na_grade(MOVIMENTO['acoes'][acao][i].get('quadril', 0)
                         * ESCALA)
    tx = R.na_grade(dx(ENCAIXE['torso'][0]))  # e lado para onde ele foi

    # O TRONCO NAO INCLINA, e a cabeca e os bracos tambem nao.
    #
    # Inclinar e um degrau: como tudo anda de dois em dois (a grade da
    # tela), inclinar o tronco 2 px nao o faz pender — faz a metade de
    # baixo dele dar um pulo de 1 px na tela enquanto a de cima fica. Em
    # 21 linhas de tronco isso nao le como inclinacao, le como o desenho
    # se partindo na altura da cintura. Medido: 32 dos ~90 pixels do
    # tronco mudavam de lugar por causa so disso.
    #
    # E o original nao perde nada com isso: medindo os quadros dele, o
    # corpo anda no maximo 1,5 px de lado a animacao inteira. O que ele
    # move de verdade e a vertical e a ponta dos membros.
    #
    # So a PERNA inclina, porque e ali que esta a passada: o quadril
    # fica e o pe viaja. E uma peca de 7 linhas, entao o degrau cai no pe
    # — que e exatamente onde a gente quer ver o movimento.

    partes = {}
    inclina = {}

    for nome, (encaixe, ponta) in ENCAIXE.items():
        # ESTE e o ponto que impede o membro de soltar: o x do encaixe
        # nao e escolhido para o membro, e copiado de onde o tronco esta.
        # ESTE e o ponto que impede o membro de soltar: ninguem escolhe
        # o proprio x. Todos recebem o do tronco.
        px = tx
        py = R.na_grade(dy(encaixe))

        if nome == 'head':
            # A CABECA PIVOTA NO PESCOCO: o queixo fica colado no tronco
            # (por isso px = tx, e o py nunca sobe em relacao a ty, senao
            # abre fresta) e o alto do cranio com as ORELHAS viaja.
            #
            # O quanto ele viaja NAO e invencao: e a diferenca do campo
            # dx lido na altura das orelhas e na altura do queixo. O
            # original mexe a cabeca exatamente assim — medindo os
            # quadros dele, as linhas das orelhas mudam de largura
            # enquanto o rosto quase nao sai do lugar.
            # A CABECA NAO INCLINA MAIS. Inclinar movia as linhas de
            # cima dela, e as linhas de cima sao o TOPO DO CRANIO. Na
            # tela, o domo do cranio pulando 1 px enquanto as orelhas
            # iam para outro lado lia como cabeca duplicada — era essa
            # a queixa de "o topo da cabeca e as orelhas ficam sendo
            # duplicadas".
            #
            # Inclinar a cabeca era, desde o inicio, so um jeito
            # indireto de dizer "as orelhas se mexem". Agora cada
            # orelha se mexe por conta propria, com a sua propria
            # caixa (ver ORELHAS no rig), e o cranio fica parado.
            partes[nome] = (px, max(py, ty))
            continue

        if nome.startswith('leg'):
            # A perna so pode subir em relacao ao tronco. Descer abre
            # buraco no quadril — e como o tronco e desenhado depois das
            # pernas, ele passa por cima e come a perna.
            if respira:
                # A PERNA SOBE JUNTO COM O TRONCO.
                #
                # Ja foi o contrario — pe cravado no chao enquanto o
                # peito subia. So que a perna nao e elastica: para o pe
                # ficar e o quadril subir, alguem tem de ESTICAR a
                # coxa, e esticar e repetir pixel. Era uma das fontes
                # dos pixels a mais, e quando nao se esticava o pe
                # simplesmente descolava do corpo.
                #
                # Subindo tudo junto, o goblin inteiro sobe 2 px do
                # sprite = UM pixel de tela. Isso nao se le como pulo,
                # se le como respiracao, e nenhum pixel e inventado.
                py = ty
            else:
                py = max(ty - 4, min(py, ty))
                py = R.na_grade(py)
            # TROCA DE PESO: para que lado as pernas foram em relacao ao
            # corpo todo. Vem do campo 'peso', medido a parte, e NAO de
            # dx: o centro de cada linha de dx mostra o membro daquela
            # linha esticando, e ler aquilo como inclinacao do corpo faz
            # o goblin inteiro tremer 1 px de tela por quadro. Medido no
            # original, o centro de massa dele anda 0,12 px no parado —
            # o corpo nao inclina, so os membros se mexem.
            #
            # O quadril fica debaixo do tronco, entao andar de lado aqui
            # nao abriria fresta. Na pratica a troca de peso do original
            # e sub-pixel e isto quase sempre da zero — fica aqui porque
            # e o lugar certo caso alguem recapture um goblin que troque
            # o peso de verdade.
            peso = R.na_grade(MOVIMENTO['acoes'][acao][i].get('peso', 0)
                              * ESCALA)
            px += max(-DESLOCA_PESO, min(DESLOCA_PESO, peso))

            # O QUADRIL GIRA. Correndo, o original nao mantem os dois pes
            # na mesma linha: nos quadros 4, 5 e 6 o pe esquerdo fica 1 px
            # acima do direito. E a bacia virando — um lado sobe e vai a
            # frente, o outro desce e fica para tras. Sem isso a corrida
            # e um boneco de pernas paralelas deslizando.
            #
            # O lado que sobe e so ele: o outro fica onde estava. Subir e
            # seguro (a perna ja so pode subir em relacao ao tronco); se
            # descesse, o tronco — que e desenhado depois — comia a perna.
            if quadril:
                # O lado de cima da bacia sobe E VAI PARA A FRENTE; o de
                # baixo fica para tras. So levantar o pe 1 px de tela nao
                # se enxerga — e o par (sobe + avanca) que faz ler como
                # quadril girando, e nao como um pe tropecando.
                sobe = (nome == 'leg_l') == (quadril > 0)
                if sobe:
                    py = R.na_grade(max(ty - 4, py - abs(quadril)))
                px += QUADRIL_GIRO if sobe else -QUADRIL_GIRO
        else:
            # O ombro nao so "nunca sobe acima do tronco": ele vai
            # exatamente junto. Deixar 1 px de diferenca entre os dois ja
            # abria uma fresta na diagonal do ombro — e um pixel de fundo
            # preto ao lado do braco e o bastante para o olho ler que ele
            # descolou.
            py = ty

        if respira:
            # RESPIRANDO: so o peito sobe e desce. Nada de membro
            # abrindo — isso e andar, nao respirar.
            partes[nome] = (px, py)
            continue

        if nome not in ESTICA:
            partes[nome] = (px, py)
            continue

        lim = ESTICA[nome]
        # QUANTO A PONTA ESTICOU, lido do lado certo e na altura certa.
        #
        # Antes isto vinha de `alcance`, que pega o extremo de uma FAIXA
        # inteira do corpo — e uma linha larga mascara o movimento das
        # vizinhas. No dano do original o ombro vai de 7 para 13 px de
        # largura e `alcance` registrava 1, porque a linha do cotovelo
        # logo abaixo ja era larga. O campo `meia` le cada altura e cada
        # lado por conta propria, no mesmo perfil de 17 amostras do dx.
        estica = meia(LADO[nome], FRACAO_PONTA[nome])
        estica = max(-lim['dentro'], min(lim['fora'], estica))
        estica = R.na_grade(estica) * lim['sinal_fora']

        # BRACO E PERNA SE MEXEM DA MESMA FORMA: INCLINANDO.
        #
        # A linha de cima da peca (ombro / quadril) fica exatamente onde o
        # campo do tronco mandou, e so a linha de baixo (mao / pe) viaja.
        # Por construcao o ombro nunca descola: ele nem chega a ser
        # deslocado. Foi essa a licao da fresta -- o erro antigo nao era
        # inclinar, era deslocar o braco INTEIRO.
        #
        # Antes o braco andava rigido e so para dentro, e o resultado era
        # um braco de apoio parado o trabalho todo. O original estica o
        # braco para fora; agora este tambem estica.
        partes[nome] = (px, py)
        if not estica:
            continue

        # O MEMBRO ANDA INTEIRO, NAO INCLINADO.
        #
        # Inclinar era deslocar cada linha um tanto diferente: a linha
        # da mao andava 4 px e a do ombro 0. Isso nao move o desenho,
        # ELE REDESENHA o desenho — a diagonal do braco vira escada, o
        # contorno abre, e para tapar o que abriu entravam a solda e o
        # "estica o ombro", que pintavam pele que o artista nao pos.
        # Dai "a qualidade diminuiu e tem pixels a mais": o braco
        # deixava de ser o braco desenhado e virava uma reamostragem
        # dele, quadro a quadro.
        #
        # Com topo == base o braco inteiro escorrega `estica` px. Cada
        # pixel chega na tela exatamente como foi pintado, o ombro
        # continua encaixado no tronco (ele sobrepoe 7 a 9 px, e o
        # passo e no maximo 4) e nao ha junta para remendar. E assim
        # que pixel art se anima: peca inteira, em pixel cheio.
        inclina[nome] = (estica, estica)

    if squash:
        # AGACHAR E O CORPO DESCER, NAO O TRONCO SER ESPREMIDO.
        #
        # Antes isto apagava 2 linhas da barra da tunica (squash_rows).
        # Apagar linha e perder desenho: a tunica mudava de forma e
        # voltava, duas vezes por golpe, e o olho le isso como o sprite
        # piscando de qualidade. Agora cabeca, bracos e tronco descem
        # 2 px inteiros e os pes ficam no chao — o joelho dobra de
        # verdade, e nenhum pixel e inventado nem perdido. O tronco
        # cobre 4 px do alto da perna, entao descer 2 nao abre nada.
        for nome in ('head', 'arm_l', 'arm_r', 'torso'):
            partes[nome] = (partes[nome][0], partes[nome][1] + squash)
        squash = 0

    if not respira:
        # UM PE SEMPRE NO CHAO.
        #
        # Os dois pes vinham do mesmo campo medido e subiam JUNTOS: em
        # metade dos quadros da corrida o goblin estava com os dois pes
        # no ar, flutuando. Nao e passada, e um boneco sendo erguido.
        #
        # Andar e isto: o pe da frente planta, o de tras descola.
        # Quem esta na frente se sabe pelo proprio passo (o shear da
        # perna), entao a regra nao precisa de tabela nenhuma e vale
        # para qualquer acao.
        passo_e = inclina.get('leg_l', (0, 0))[1]
        passo_d = inclina.get('leg_r', (0, 0))[1]
        if passo_e != passo_d:
            frente = 'leg_l' if passo_e > passo_d else 'leg_r'
            tras = 'leg_r' if frente == 'leg_l' else 'leg_l'
            ty_ = partes['torso'][1]
            partes[frente] = (partes[frente][0], ty_)
            partes[tras] = (partes[tras][0], max(ty_ - 2,
                                                 partes[tras][1]))
        else:
            # parado de pe sobre os dois: ninguem flutua
            for nome in ('leg_l', 'leg_r'):
                partes[nome] = (partes[nome][0], partes['torso'][1])

    # A arma acompanha a mao que a segura (parte arm_r), inclusive a
    # inclinacao do punho. Se cada animacao repetisse esse valor na mao,
    # bastaria esquecer de atualizar um deles para a arma equipada
    # flutuar longe do punho — ja aconteceu.
    # As ORELHAS abrem e fecham. Medido no original (campo 'orelhas' do
    # orig_movimento.json): a faixa das pontas muda ate 1 px de largura
    # na tela de 32, que sao 2 aqui — 1 px para cada ponta, arredondado
    # para a grade da tela.
    orelhas = R.na_grade(MOVIMENTO['acoes'][acao][i].get('orelhas', 0)
                         * ESCALA / 2)
    # e uma das duas pontas CAI, tambem medido no original
    cai = R.na_grade(MOVIMENTO['acoes'][acao][i].get('orelha_cai', 0)
                     * ESCALA)

    pose = {
        **partes,
        'sword': (0, 0),
        '_sword': kind,
        # ORELHAS PARADAS, DE PROPOSITO.
        #
        # Elas ja se mexeram aqui, e foi um dos focos de "pixels a
        # mais". A orelha tem 3 px de espessura e tudo neste rig anda
        # de 2 em 2 px (um pixel de tela): uma orelha de 3 px dando um
        # salto de 2 nao balanca, ela se desmonta — e para ela nao se
        # desmontar era preciso reamostrar celula por celula, que e
        # justamente o que borra o desenho. No original a variacao
        # medida e de 1 px na tela de 32; nao vale o preco.
        '_ears': None,
        '_ear_drop': None,
        '_squash': {'torso': squash} if squash else None,
        '_shear': inclina or None,
    }
    # Antes de entregar: recolher o que nao encosta. Melhor um braco 2 px
    # menos esticado do que o rig ter de pintar pele por cima do fundo
    # para colar a mao de volta no corpo.
    pose = _encaixar(pose, inclina)

    # a arma anda com o punho, entao so da para posiciona-la depois que
    # o braco parou de ser ajustado
    mao = partes['arm_r']
    punho = (pose.get('_shear') or {}).get('arm_r', (0, 0))[1]
    pose['sword'] = (mao[0] + punho, mao[1])
    return pose


# ===================================================================== #
#  A REGRA DE OURO DAS ANIMACOES                                        #
# ===================================================================== #
# O goblin se partia no meio, a perna sumia no trabalho e o braco ficava
# solto no ar. A causa era sempre a mesma: cada peca recebia um numero
# escolhido para ela, e nada garantia que o numero do braco combinasse
# com o do tronco. Bastavam 4 px em sentidos opostos para abrir a cintura
# — e, como o tronco e desenhado DEPOIS das pernas, ele passava por cima
# e comia a perna inteira.
#
# Agora vale isto, e o anim_test.py cobra:
#
#   1. NINGUEM ESCOLHE O PROPRIO DESLOCAMENTO. Ombro e quadril leem o
#      campo do original na linha em que encostam no tronco, que e a
#      mesma linha que o tronco le. Mesmo valor, mesma funcao.
#   2. QUEM SE MEXE E A PONTA. Mao e pe viajam por INCLINACAO: a linha de
#      cima da peca fica onde esta e a de baixo anda.
#   3. PERNA SO SOBE, no maximo 4 px.
#   4. A CABECA NUNCA SOBE SOZINHA, e nunca inclina (o rosto e pintado
#      depois, na posicao dela).
#
# Com isso o corpo e sempre uma peca so, e ainda assim cada parte se mexe.


# --------------------------------------------------------------- idle ------
# Parado: ele RESPIRA. O peito sobe 2 px e volta com os pes plantados no
# chao, e so as orelhas se mexem alem disso.
#
# Antes o parado usava a mesma montagem das outras acoes e saia com os
# bracos e as pernas abrindo e o corpo inteiro quicando — ficava com
# cara de quem esta andando parado no lugar. Respirar e outra coisa: o
# que se mexe e o tronco, e o pe nao sai do lugar.
# ===================================================================== #
#  OS QUADROS, UM POR UM                                                #
# ===================================================================== #
# Ate aqui as poses eram CALCULADAS: um campo medido do goblin antigo
# (orig_movimento.json) era lido, escalado e clampeado, e o que saia do
# outro lado ninguem tinha desenhado. Dava braco entrando no corpo,
# queixo esticado, os dois pes no ar e o quadril sem girar — defeitos
# que nao estao em lugar nenhum da tabela, nascem da conta.
#
# Agora cada quadro e escrito a mao, numero por numero. E mais
# trabalhoso e e exatamente por isso que funciona: da para olhar o
# quadro 3 da caminhada e consertar SO ele.
#
# AS REGRAS QUE TODO QUADRO OBEDECE (o teste cobra cada uma):
#
#  1. Tudo em numero PAR. Um pixel do sprite e meio pixel da tela; so o
#     par sobrevive a reducao sem reserrar o desenho.
#  2. A CABECA ANDA COM O TRONCO, sempre. Foi deixar a cabeca com vida
#     propria que esticou o queixo: a cabeca subia, o tronco ficava, e
#     o vao entre os dois era tapado com contorno — virava papada.
#  3. O BRACO NUNCA VAI PARA DENTRO. O tronco e desenhado antes do
#     braco direito e depois do esquerdo; um braco andando para o
#     centro some atras do peito ou e comido por ele. Braco recolhe
#     para CIMA (dy negativo), nunca para dentro.
#  4. UM PE SEMPRE NO CHAO, e o pe plantado nao se mexe.
#  5. O CORPO SO AFUNDA, nunca flutua. Subir o tronco descobre o alto
#     da perna e abre o quadril; afundar so aumenta a sobreposicao. E
#     anatomicamente certo: o corpo baixa quando o peso cai sobre a
#     perna.
#
# Convencao das tabelas: (dx, dy) de cada peca, em pixels do sprite de
# 64. `corpo` move cabeca, tronco, bracos e a arma juntos; as pernas
# sao ABSOLUTAS (o pe plantado tem de ignorar o balanco do corpo).

def _quadro(corpo=(0, 0), braco_e=(0, 0), braco_d=(0, 0),
            perna_e=(0, 0), perna_d=(0, 0), kind='diag',
            orelha_e=0, orelha_d=0, rosto=None):
    """Um quadro escrito a mao. `braco_e` e o braco do lado esquerdo da
    tela (parte arm_l); `braco_d` segura a arma (parte arm_r)."""
    bx, by = corpo
    return {
        'head': (bx, by),
        'torso': (bx, by),
        'arm_l': (bx + braco_e[0], by + braco_e[1]),
        'arm_r': (bx + braco_d[0], by + braco_d[1]),
        'leg_l': perna_e,
        'leg_r': perna_d,
        'sword': (bx + braco_d[0], by + braco_d[1]),
        '_sword': kind,
        # as orelhas andam em BLOCO, 2 px (ver rig.mexe_orelhas): a
        # da esquerda (deitada) sobe e desce, a da direita (em pe)
        # balanca de lado
        '_ears': orelha_e or None,
        '_ear_drop': orelha_d or None,
        '_rosto': rosto,
        '_squash': None,
        '_shear': None,
    }


# --------------------------------------------------------------- idle ------
# RESPIRAR E AFUNDAR UM PIXEL E VOLTAR.
#
# Cinco quadros: solta o ar (afunda 2 px = 1 px de tela), segura,
# enche de novo. Os pes nao saem do lugar e a cabeca acompanha o
# tronco, entao nao ha junta nenhuma se abrindo — e a animacao que
# o goblin passa 90% do tempo fazendo, entao ela tem de ser a mais
# limpa de todas.
IDLE = [
    _quadro(),
    _quadro(corpo=(0, 2), orelha_e=2),
    _quadro(corpo=(0, 2), orelha_e=2, orelha_d=-2),
    _quadro(corpo=(0, 2), braco_e=(0, -2), orelha_d=-2),
    _quadro(),
]


def idle_poses():
    return [dict(q) for q in IDLE]


# --------------------------------------------------------------- walk ------
# O CICLO DE CAMINHADA, QUADRO A QUADRO.
#
# Oito quadros = dois passos de quatro tempos. Cada passo:
#
#   contato  o pe da frente encosta, o corpo AFUNDA 2 e o peso passa
#            para esse lado (o tronco desloca 2 px para la)
#   apoio    o corpo sobe de volta e a perna de tras descola do chao
#   passagem a perna solta cruza por baixo do corpo
#   alcance  ela se estende para o proximo contato e o corpo afunda
#
# O QUADRIL GIRA porque as duas pernas nunca fazem a mesma coisa: a
# plantada fica parada e assume o peso, a solta sobe 2 px e muda de x.
# Como o tronco tambem desloca para o lado do apoio, a bacia lida pelo
# olho e uma bacia girando, nao duas pernas paralelas deslizando.
#
# OS BRACOS VAO AO CONTRARIO DAS PERNAS, como numa pessoa: perna
# esquerda solta -> braco direito para a frente. E eles so abrem para
# FORA (ver regra 3).
def _passo(lado):
    """Quatro quadros de um passo. `lado` = +1 planta a direita.

    O TRONCO NAO GINGA. Ele ja gingou 2 px para cada lado e o goblin
    pareceu estar dancando: na vista de frente, corpo indo e voltando
    de lado le como samba, nao como caminhada. Quem mostra o passo sao
    as PERNAS — e e justamente por o tronco ficar parado que o giro do
    quadril aparece.
    """
    s = 2 * lado
    plantada, solta = ('perna_d', 'perna_e') if lado > 0 else \
                      ('perna_e', 'perna_d')
    # BRACO CONTRARIO A PERNA QUE SAI DO CHAO: perna esquerda solta ->
    # braco direito abre. E assim que uma pessoa anda; com o braco do
    # mesmo lado o goblin anda feito soldadinho de chumbo.
    braco = 'braco_d' if solta == 'perna_e' else 'braco_e'
    fora = -2 if braco == 'braco_e' else 2
    outro = 'braco_e' if braco == 'braco_d' else 'braco_d'
    quadros = []
    for k, (afunda, sobe_pe, desvio, abre, orelha) in enumerate((
            # desvio da perna solta: 4 px de abertura no contato e zero
            # na passagem — e este vai-e-vem que o olho le como PASSO.
            # sobe_pe de 4 px sao 2 pixels de tela: com 2 o pe mal
            # descolava e a caminhada lia como deslizada.
            (2, 0, -2 * s, 0, 0),      # contato: os dois pes no chao
            (0, -4, -s, fora, 2),      # apoio: a perna de tras descola
            (0, -4, 0, fora, 2),       # passagem: cruza sob o corpo
            (2, 0, s, 0, 0))):         # alcance: estende para o proximo
        arg = {'corpo': (0, afunda),
               plantada: (0, 0),
               solta: (desvio, sobe_pe),
               # O BRACO INTEIRO, nao so a mao: ele abre `fora` E
               # sobe 2 px no mesmo quadro. Foi a queixa de "mexa o
               # outro braco inteiro" — abrindo so de lado, o ombro
               # ficava plantado e parecia que so a mao balancava.
               braco: (abre, -2 if abre else 0),
               # e o outro fica onde esta: DESCER o braco tira o ombro
               # de baixo do tronco e abre a junta (so subir e seguro)
               outro: (0, 0),
               # as orelhas sacodem junto com o passo
               'orelha_e': orelha,
               'orelha_d': -orelha}
        quadros.append(_quadro(**arg))
    return quadros


WALK = _passo(+1) + _passo(-1)


def walk_poses():
    return [dict(q) for q in WALK]


# ------------------------------------------------------------- attack ------
# O SOCO, QUADRO A QUADRO. Quatro tempos, repetidos ate os 17 quadros.
#
#   arma     ergue o punho (dy -2). RECOLHER PARA TRAS ESTAVA ERRADO:
#            puxar o braco para dentro o enfiava atras do peito.
#            Levantar mostra o movimento inteiro e nao cobre nada.
#   bate     o punho vai para fora e o CORPO avanca e afunda junto —
#            e o corpo que da peso ao golpe, nao o braco esticando.
#   segura   o impacto fica um tempo parado; sem isso o soco vira
#            tremelique.
#   volta    base.
#
# As pernas abrem a base (uma para cada lado, as duas no chao): e o
# apoio de quem bate. Elas nao se mexem durante o golpe — quem bate
# firma os pes.
ATTACK_KIND = [['up', 'down', 'down', 'diag'][i % 4] for i in range(17)]
SOCO = [
    # (corpo, braco esq, braco dir, perna esq, perna dir, orelhas, cara)
    ((0, 0), (0, -2), (0, -2), (-2, 0), (2, 0), (2, -2), 'bravo'),
    ((2, 2), (-2, -2), (2, 0), (-4, 0), (4, 0), (2, -2), 'bravo'),
    ((2, 2), (-2, -2), (2, 0), (-4, 0), (4, 0), (2, -2), 'bravo'),
    ((0, 0), (0, 0), (0, 0), (-2, 0), (2, 0), (0, 0), None),
]


def attack_poses():
    saida = []
    for i in range(FRAME_COUNTS['attack']):
        corpo, be, bd, pe, pd, orelhas, cara = SOCO[i % 4]
        saida.append(_quadro(corpo=corpo, braco_e=be, braco_d=bd,
                             perna_e=pe, perna_d=pd,
                             orelha_e=orelhas[0], orelha_d=orelhas[1],
                             rosto=cara, kind=ATTACK_KIND[i]))
    return saida


# --------------------------------------------------------------- hurt ------
# LEVAR O GOLPE, QUADRO A QUADRO. Quatro poses, cada uma segurada por
# quatro quadros — o tranco tem de durar o bastante para o jogador ver
# o que aconteceu.
#
#   1. o impacto: o corpo recua 2 e afunda 2, os dois bracos abrem
#   2. o pior momento: recua mais, bracos bem abertos, base aberta
#   3. comeca a se recompor
#   4. de volta
#
# O clarao vermelho e do pos-processo (HURT_FLASH).
HURT_FLASH = {0, 1, 2, 3, 4, 5, 6, 7}
HURT_SEGURA = 4

# A CARA DE DOR e as orelhas caidas fazem metade do trabalho: o corpo
# recua poucos pixels, mas um rosto apertado le na hora.
DANO = [
    _quadro(corpo=(-2, 2), braco_e=(-2, -2), braco_d=(2, -2),
            perna_e=(-2, 0), perna_d=(2, 0),
            orelha_e=2, orelha_d=-2, rosto='dor'),
    # o braco abre no maximo 2 px alem do tronco: com 4 a mao perde o
    # contato com o corpo na reducao para a tela e fica boiando
    _quadro(corpo=(-2, 2), braco_e=(-2, -2), braco_d=(2, -2),
            perna_e=(-4, 0), perna_d=(4, 0),
            orelha_e=2, orelha_d=-2, rosto='dor'),
    _quadro(corpo=(0, 2), braco_e=(-2, 0), braco_d=(2, 0),
            perna_e=(-2, 0), perna_d=(2, 0),
            orelha_e=2, rosto='dor'),
    _quadro(),
]


def hurt_poses():
    saida = []
    for i in range(FRAME_COUNTS['hurt']):
        p = dict(DANO[min(i // HURT_SEGURA, len(DANO) - 1)])
        p['_flash'] = i in HURT_FLASH
        saida.append(p)
    return saida


# -------------------------------------------------------------- death ------
# Antes a morte tinha 15 quadros e, no quadro 7, o goblin simplesmente
# APARECIA deitado — teleportava para o chao. Agora sao 24 quadros e a
# queda acontece:
#
#   0-2    cambaleia, perde o equilibrio
#   3-8    os joelhos cedem: o corpo afunda 11 px, a cabeca pende
#   9-11   de joelhos, o tronco tomba para a frente
#   12     perde o contato com o chao (quadro de queda, corpo no ar)
#   13-14  bate no chao e quica uma vez
#   15-18  acomoda: os membros se ABREM, como na referencia
#   19-23  imovel, sumindo
#
# LIMITE HONESTO: pixel art nao aceita rotacao em angulo qualquer — girar
# 45 graus reamostra e destroi o desenho. O corpo deitado usa rotacao de
# exatos 90 graus (sem perder um pixel) e o esparramado da referencia e
# reproduzido ABRINDO os membros: cada parte ganha um deslocamento antes da
# rotacao, entao no chao o goblin fica com a cabeca num extremo, os bracos
# abertos (um para cima, outro para baixo) e as pernas afastadas.
DEATH_FRAMES = 12

# --- como a morte foi montada ---------------------------------------------
# Nao ha queda nenhuma. O golpe final mata na hora: o PRIMEIRO quadro da
# animacao ja mostra o goblin no chao. Em cima dele estoura uma luz
# vermelha e a palavra GOBLINZED e escrita de tres em tres letras.
#
#   0      BAQUE     ele ja aparece caido, a luz no auge
#   1-3    ESCRITA   GOBLINZED entra em tres lances (3, 6 e 9 letras)
#   4-6    ESPERA    a palavra inteira, a luz comecando a esvaziar
#   7-11   APAGA     luz, palavra e corpo somem juntos
#
# Sao 12 quadros, metade do que era: o pedido foi que fosse mais rapido e
# que ele ja aparecesse no chao, sem agachar e sem tombar.

GOBLINZED = 'GOBLINZED'
GOBLINZED_DEITA = 0           # ele ja comeca caido: a morte e instantanea

# Quantas letras ja foram escritas em cada quadro — de tres em tres, para
# a palavra inteira estar na tela ja no quarto quadro.
GOBLINZED_LETRAS = [0, 3, 6, 9] + [9] * 8

# Opacidade da palavra: entra inteira com as primeiras letras e so apaga
# no fim, junto com o corpo.
GOBLINZED_ALPHA = [0] + [255] * 6 + [228, 188, 142, 94, 46]

# Forca da luz vermelha, de 0 a 1. Estoura no baque e vai esvaziando.
DEATH_GLOW = [1.0, 0.95, 0.90, 0.84, 0.74, 0.60, 0.48,
              0.36, 0.26, 0.17, 0.09, 0.0]

DEATH_ALPHA = ([255] * 8) + [226, 188, 144, 98]


def death_poses():
    """Todo quadro da morte ja e o corpo no chao. Nao ha pose de pe."""
    out = []
    for i in range(DEATH_FRAMES):
        p = {k: None for k in R.DRAW_ORDER}
        p['_lay'] = (0, 0)
        # a mao continua sendo uma ancora: a arma equipada cai junto
        p['sword'] = (0, 0)
        p['_sword'] = 'fwd'
        p['_eyes_shut'] = True
        p['_dead'] = i
        out.append(p)
    return out


POSES = {
    'idle': idle_poses,
    'walk': walk_poses,
    'attack': attack_poses,
    'hurt': hurt_poses,
    'death': death_poses,
}


# ---------------------------------------------------------- pos-processo ----
# O que transforma os quadros de pe em quadros de MORTE nao esta no rig:
# e a luz vermelha e a palavra GOBLINZED, as duas aplicadas aqui, depois
# de o corpo ja estar desenhado.
#
# As duas sao desenhadas de forma DETERMINISTICA — nao dependem da
# silhueta do quadro. Isso importa porque o gerador de equipamento monta
# cada overlay como a diferenca entre o quadro vestido e o quadro nu: se a
# luz seguisse o contorno, cada armadura levaria junto uma franja vermelha
# que nao e dela. Do jeito que esta, luz e letras se cancelam na subtracao
# e o overlay sai so com a peca.

VERMELHO = (255, 64, 48)          # a luz
LETRA = (236, 42, 42)             # o corpo da letra
LETRA_ALTO = (255, 138, 120)      # o brilho em cima da letra
LETRA_BORDA = (56, 6, 10)         # o contorno, para ler sobre qualquer fundo

GLOW_CENTRO = (32, 34)
GLOW_RAIO = 26
GLOW_FAIXAS = (140, 100, 62, 28)          # degraus de opacidade, do centro


def _halo():
    """Auréola vermelha, desenhada uma vez e reaproveitada.

    Em DEGRAUS chapados, nao em degrade continuo: alem de combinar com o
    resto da arte, um degrade de 64x64 em cada um dos 24 quadros de morte
    de cada variacao engordava o jogo em megabytes de pixel quase igual.
    """
    if _halo.cache is None:
        img = Image.new('RGBA', (R.SIZE, R.SIZE), (0, 0, 0, 0))
        px = img.load()
        cx, cy = GLOW_CENTRO
        n = len(GLOW_FAIXAS)
        for y in range(R.SIZE):
            for x in range(R.SIZE):
                d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 / GLOW_RAIO
                if d < 1.0:
                    px[x, y] = VERMELHO + (GLOW_FAIXAS[min(n - 1, int(d * n))],)
        _halo.cache = img
    return _halo.cache


_halo.cache = None


def _brilho(img, k):
    """Banha o quadro em luz vermelha: halo por tras e tinta no corpo."""
    if k <= 0:
        return img
    halo = _halo().copy()
    # o k tambem anda em degraus, para os quadros se repetirem mais
    passo = max(1, int(round(k * 8)))
    halo.putalpha(halo.getchannel('A').point(lambda v: v * passo // 8))
    fundo = Image.new('RGBA', img.size, (0, 0, 0, 0))
    fundo.alpha_composite(halo)
    # tinta: mistura cada pixel do corpo com o vermelho, sem mexer no alfa
    corpo = img.convert('RGBA')
    chapa = Image.new('RGBA', img.size, VERMELHO + (255,))
    chapa.putalpha(corpo.getchannel('A'))
    # a tinta tambem anda em degraus: quadros vizinhos saem iguais e o
    # arquivo unico do jogo nao engorda com 24 vermelhos quase iguais
    corpo = Image.blend(corpo, chapa, round(min(0.62, 0.62 * k) * 4) / 4)
    corpo.putalpha(img.getchannel('A'))
    fundo.alpha_composite(corpo)
    return fundo


# Fonte 4x5 so com as letras de GOBLINZED. E o maior tamanho que deixa a
# palavra inteira (9 letras = 44 px) caber nos 64 px do quadro.
FONTE = {
    'G': ['####', '#...', '#.##', '#..#', '####'],
    'O': ['####', '#..#', '#..#', '#..#', '####'],
    'B': ['###.', '#..#', '###.', '#..#', '###.'],
    'L': ['#...', '#...', '#...', '#...', '####'],
    'I': ['####', '.##.', '.##.', '.##.', '####'],
    'N': ['#..#', '##.#', '#.##', '#..#', '#..#'],
    'Z': ['####', '...#', '.##.', '#...', '####'],
    'E': ['####', '#...', '###.', '#...', '####'],
    'D': ['###.', '#..#', '#..#', '#..#', '###.'],
}
LETRA_W, LETRA_H, LETRA_GAP = 4, 5, 1
TEXTO_Y = 7


def _escrever(img, letras, alpha):
    """Escreve GOBLINZED por cima do quadro, da esquerda para a direita."""
    if letras <= 0 or alpha <= 0:
        return img
    passo = LETRA_W + LETRA_GAP
    largura = len(GOBLINZED) * passo - LETRA_GAP
    x0 = (R.SIZE - largura) // 2
    marcados = set()
    for n, ch in enumerate(GOBLINZED[:letras]):
        bx = x0 + n * passo
        for dy, linha in enumerate(FONTE[ch]):
            for dx, c in enumerate(linha):
                if c == '#':
                    marcados.add((bx + dx, TEXTO_Y + dy))
    camada = Image.new('RGBA', img.size, (0, 0, 0, 0))
    px = camada.load()
    # contorno primeiro, para a palavra ler sobre o corpo e sobre o fundo
    for (x, y) in marcados:
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                q = (x + ox, y + oy)
                if q not in marcados and 0 <= q[0] < R.SIZE and 0 <= q[1] < R.SIZE:
                    px[q] = LETRA_BORDA + (255,)
    for (x, y) in marcados:
        # a linha de cima de cada letra e mais clara: da relevo
        px[x, y] = (LETRA_ALTO if (x, y - 1) not in marcados else LETRA) + (255,)
    camada.putalpha(camada.getchannel('A').point(lambda v: v * alpha // 255))
    out = img.copy()
    out.alpha_composite(camada)
    return out


def _fade(img, alpha):
    if alpha >= 255:
        return img
    a = img.getchannel('A').point(lambda v: v * alpha // 255)
    img = img.copy()
    img.putalpha(a)
    return img


def _flash(buf):
    """O quadro de impacto fica VERMELHO, nao mais claro.

    Clarear a pele era o efeito errado: o goblin so ficava mais
    palido, e a leitura era "mudou de cor", nao "levou pancada". O
    clarao vermelho e a convencao do genero — e aqui ele nao inventa
    cor nenhuma: 'r' e 'R' ja sao a dupla de vermelhos da paleta,
    usada nas marcas das variacoes.
    """
    golpe = {'e': 'R', 'd': 'R', 'n': 'R', 'j': 'r', 'g': 'r', 'l': 'r',
             'B': 'R', 'b': 'R', 'h': 'r', 'c': 'R'}
    for y in range(R.SIZE):
        for x in range(R.SIZE):
            c = buf[y][x]
            if c in golpe:
                buf[y][x] = golpe[c]


def post(img, pose, efeitos=True):
    """Pos-processo da morte: luz vermelha, desvanecer e a palavra.

    `efeitos=False` devolve so o corpo, sem luz nem letras. E o que os
    testes usam: a palavra GOBLINZED e, de proposito, um pedaco solto do
    desenho, e sem esta chave ela seria reprovada como membro descolado.
    """
    k = pose.get('_dead')
    if k is None:
        return img
    if efeitos:
        img = _brilho(img, DEATH_GLOW[k])
    img = _fade(img, DEATH_ALPHA[k])
    if efeitos:
        img = _escrever(img, GOBLINZED_LETRAS[k], GOBLINZED_ALPHA[k])
    return img


def render_action(action, variation=None, efeitos=True):
    """Retorna a lista de Images de uma animacao, ja com a variacao aplicada."""
    frames = []
    swap = variation.get('swap') if variation else None
    parts = variation.get('parts') if variation else None
    detail = variation.get('detail') if variation else None
    for i, pose in enumerate(POSES[action]()):
        buf = R.compose(pose, variation=detail, swap=swap, extra_parts=parts)
        if pose.get('_flash'):
            _flash(buf)
        frames.append(post(R.to_image(buf), pose, efeitos))
    assert len(frames) == FRAME_COUNTS[action], (action, len(frames))
    return frames


def render_all(variation=None):
    return {a: render_action(a, variation) for a in ACTIONS}


if __name__ == '__main__':
    import os
    os.makedirs('/tmp/prev', exist_ok=True)
    all_frames = render_all()
    rows = [all_frames[a] for a in ACTIONS]
    w = max(len(r) for r in rows)
    sheet = Image.new('RGBA', (32 * w, 32 * len(rows)), (26, 26, 30, 255))
    for j, r in enumerate(rows):
        for i, im in enumerate(r):
            sheet.alpha_composite(im, (i * 32, j * 32))
    sheet.resize((sheet.width * 5, sheet.height * 5), Image.NEAREST).save('/tmp/prev/anim.png')
    print('ok')
