#!/usr/bin/env python3
"""Le o movimento do PRIMEIRO goblin e o escreve numa tabela.

O goblin velho era 32x32 e tinha cada quadro desenhado na mao. O novo e
64x64 e e montado por um rig que desloca e inclina pecas. Nao da para
copiar os pixels de um no outro — sao desenhos diferentes. O que da para
copiar, e e o que o jogo mostra, e o MOVIMENTO: quanto cada altura do
corpo subiu, desceu e andou para o lado em cada quadro.

E isso que este arquivo faz. Para cada quadro original ele mede, linha
por linha, onde esta o centro do corpo e onde estao o topo e a base. Sai
um campo continuo — "nesta altura o corpo andou tanto" — que o
goblin_anim.py depois le para mover o rig novo.

Medir linha por linha nao e um detalhe: e o que impede o braco de soltar.
Braco e tronco pegam o deslocamento da MESMA funcao continua, na altura
em que cada um encosta no outro, entao os dois chegam no mesmo lugar por
construcao. Nao ha numero escolhido a mao que possa separar os dois.

Entrada:  art-source/goblins-originais/<acao>_<n>.png  (32x32, do primeiro
          goblin, resgatados do commit bf9f49e)
Saida:    tools/orig_movimento.json

Rode com:  python3 tools/orig_captura.py
"""
import json
import os

from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
ORIGINAIS = os.path.join(RAIZ, 'art-source', 'goblins-originais')
SAIDA = os.path.join(AQUI, 'orig_movimento.json')

# Quantos quadros tem cada acao no goblin original.
ACOES = {'idle': 5, 'walk': 8, 'attack': 17, 'hurt': 17, 'death': 15}

# O quadro parado e a referencia de todas as acoes. Da para conferir que
# ele serve: attack_0, hurt_0 e death_0 medem exatamente o mesmo que
# idle_0 (topo 16, base 31, centro 15.33) — as tres animacoes comecam da
# pose parada, como era de se esperar.
REPOUSO = ('idle', 0)

# Em quantos pontos o campo e amostrado entre o topo e a base do corpo.
# 17 pontos dao um passo de ~1 px no corpo original, que tem 15 linhas:
# mais que isso so copiaria o ruido do arredondamento.
AMOSTRAS = 17


def _classifica(p):
    """Pele, roupa, arma — ou nada, se o pixel for transparente."""
    r, g, b, a = p
    if a < 128:
        return None
    if g > r + 18 and g > b + 10:
        return 'pele'
    if r > 120 and g > 120 and b > 120:
        return 'arma'
    return 'roupa'


def _corpo(caminho):
    """Pixels do CORPO (pele e roupa), por linha.

    A arma fica de fora de proposito. Ela e comprida, sai muito para o
    lado e mexe sozinha: se entrasse na conta, o centro da linha do peito
    pularia por causa da adaga e o tronco inteiro iria atras dela.
    """
    im = Image.open(caminho).convert('RGBA')
    px = im.load()
    linhas = {}
    for y in range(im.height):
        xs = [x for x in range(im.width)
              if _classifica(px[x, y]) in ('pele', 'roupa')]
        if xs:
            linhas[y] = xs
    return linhas


def _suaviza(v, raio):
    """Media movel simples, com as pontas presas no proprio valor."""
    n = len(v)
    return [sum(v[max(0, k - raio):min(n, k + raio + 1)])
            / len(v[max(0, k - raio):min(n, k + raio + 1)])
            for k in range(n)]


def _alcance(linhas):
    """Ate onde chegam as maos e os pes neste quadro.

    O campo de centros nao enxerga um braco que ESTICA: esticar um braco
    para a esquerda e outro para a direita na mesma medida nao mexe o
    centro da linha nenhum. Mas e justamente disso que o ataque do goblin
    velho e feito — ele abre os dois bracos. Entao as pontas sao medidas
    a parte, pelo extremo de cada lado.

    Faixa dos bracos: do peito a cintura (35%% a 75%% da altura).
    Faixa dos pes: o quarto de baixo.
    """
    topo, base = min(linhas), max(linhas)
    altura = max(1, base - topo)

    def extremos(a, b):
        xs = [x for y, lst in linhas.items()
              if topo + altura * a <= y <= topo + altura * b for x in lst]
        return (min(xs), max(xs)) if xs else (0, 0)

    b_esq, b_dir = extremos(0.35, 0.75)
    p_esq, p_dir = extremos(0.75, 1.0)
    return {'braco_esq': b_esq, 'braco_dir': b_dir,
            'pe_esq': p_esq, 'pe_dir': p_dir}


def _perfil(linhas):
    """Transforma as linhas num campo amostrado em AMOSTRAS alturas.

    Devolve (topo, base, centros) com `centros[k]` = centro do corpo na
    altura k/(AMOSTRAS-1) do caminho entre o topo e a base.
    """
    topo, base = min(linhas), max(linhas)
    altura = max(1, base - topo)
    centros = []
    for k in range(AMOSTRAS):
        y = topo + altura * k / (AMOSTRAS - 1)
        # interpola entre as duas linhas vizinhas para o campo nao ficar
        # em degraus de 1 px
        y0 = int(y)
        y1 = min(base, y0 + 1)
        t = y - y0
        c = []
        for yy, peso in ((y0, 1 - t), (y1, t)):
            xs = linhas.get(yy)
            if xs:
                c.append((sum(xs) / len(xs), peso))
        if not c:
            centros.append(centros[-1] if centros else 0.0)
        else:
            total = sum(p for _, p in c) or 1.0
            centros.append(sum(v * p for v, p in c) / total)
    return topo, base, centros


def _orelhas(linhas):
    """Quanto as duas ORELHAS estao abertas neste quadro.

    O campo dx nao serve para isto, e de proposito: ele e suavizado
    justamente para a orelha nao arrastar a cabeca inteira atras dela
    (ver o comentario em capturar()). So que a orelha SE MEXE, e bastante
    — medindo os quadros do original alinhados pelo topo do corpo, a
    largura da faixa das orelhas vai de 11 a 13 px. Ela abre e fecha.

    Entao ela e medida a parte, como as maos e os pes: a largura da
    faixa de cima do corpo (5%% a 25%% da altura), que e onde ficam as
    duas pontas.
    """
    # Linhas 1 a 3 contadas do TOPO do corpo, nao uma fracao da altura:
    # o corpo muda de altura entre os quadros (ele quica), e uma fracao
    # faria a faixa escorregar para fora das orelhas.
    topo = min(linhas)
    larguras = [max(linhas[y]) - min(linhas[y]) + 1
                for y in range(topo + 1, topo + 4) if y in linhas]
    return max(larguras) if larguras else 0


def _vaos(linhas):
    """Quao ABERTOS estao os bracos e as pernas neste quadro.

    `_alcance` mede ate onde chega cada ponta, e isso nao e a mesma
    coisa. Quando o goblin abre as duas pernas, o envelope externo mal
    se mexe se ele tambem desce um pouco — mas a LARGURA da faixa dos
    pes dobra. Medindo o original, a largura da faixa dos pes varia 62%
    da altura do corpo ao longo da corrida, e a dos bracos 50%. Era o
    movimento que mais faltava no goblin novo.

    Faixas iguais as de `_alcance`: bracos do peito a cintura, pes no
    quarto de baixo.
    """
    topo, base = min(linhas), max(linhas)
    altura = max(1, base - topo)

    def largura(a, b):
        xs = [x for y, lst in linhas.items()
              if topo + altura * a <= y <= topo + altura * b for x in lst]
        return (max(xs) - min(xs) + 1) if xs else 0

    return {'bracos': largura(0.35, 0.75), 'pes': largura(0.75, 1.0)}


def _peso(linhas):
    """Para que lado as PERNAS estao, em relacao ao corpo todo.

    No parado do original o corpo nao anda de lado nenhum (o centro de
    massa varia 0,12 px nos cinco quadros), mas as linhas dos pes andam
    ate 1,5 px: ele troca o peso de um pe para o outro sem mexer o
    tronco. Como o quadril fica escondido debaixo do tronco, da para
    copiar isso sem abrir fresta.
    """
    topo, base = min(linhas), max(linhas)
    altura = max(1, base - topo)
    todos = [x for lst in linhas.values() for x in lst]
    pes = [x for y, lst in linhas.items()
           if y >= topo + altura * 0.75 for x in lst]
    if not todos or not pes:
        return 0.0
    return sum(pes) / len(pes) - sum(todos) / len(todos)


def _quadril(linhas):
    """Desnivel entre os dois pes: o QUADRIL girando.

    Correndo, o goblin original nao mantem os dois pes na mesma linha —
    nos quadros 4, 5 e 6 o pe esquerdo fica 1 px acima do direito e nos
    outros eles emparelham. Isso e a bacia virando: um lado sobe e vai a
    frente enquanto o outro desce e fica para tras. Sem isso a corrida e
    um boneco de pernas paralelas deslizando.

    Positivo = o pe ESQUERDO esta mais alto.
    """
    topo, base = min(linhas), max(linhas)
    altura = max(1, base - topo)
    todos = [x for lst in linhas.values() for x in lst]
    meio = (min(todos) + max(todos)) / 2
    fundo = {}
    for lado in (0, 1):
        ys = [y for y, lst in linhas.items() if y >= topo + altura * 0.70
              and any((x < meio) == (lado == 0) for x in lst)]
        fundo[lado] = max(ys) if ys else base
    return fundo[1] - fundo[0]


def _orelha_caida(linhas):
    """Desnivel entre as duas pontas da cabeca: uma orelha caindo.

    Mesma ideia do quadril, na outra ponta do corpo. No original a ponta
    esquerda desce 1 linha em alguns quadros enquanto a direita fica.

    Positivo = a ponta ESQUERDA esta mais baixa.
    """
    topo = min(linhas)
    todos = [x for lst in linhas.values() for x in lst]
    meio = (min(todos) + max(todos)) / 2
    alto = {}
    for lado in (0, 1):
        ys = [y for y in range(topo, topo + 4)
              if y in linhas and any((x < meio) == (lado == 0)
                                     for x in linhas[y])]
        alto[lado] = min(ys) - topo if ys else 0
    return alto[0] - alto[1]


def _meia_largura(linhas, amostras):
    """De cada lado, a que distancia do centro o corpo chega, por ALTURA.

    Esta e a medida que faltava. `_alcance` e `_vaos` pegam o extremo de
    uma FAIXA inteira do corpo, e uma linha larga mascara o movimento
    das vizinhas: no dano do original o ombro vai de 7 para 13 px de
    largura e as duas medidas antigas registram 1, porque a linha do
    cotovelo, logo abaixo, ja era larga.

    Aqui cada altura e lida por conta propria e cada lado por conta
    propria, no mesmo perfil de 17 amostras do dx e do dy. Assim o
    braco esquerdo recebe o que o lado esquerdo daquela altura fez, sem
    media com nada.
    """
    topo, base = min(linhas), max(linhas)
    vao = max(1, base - topo)
    todos = [x for lst in linhas.values() for x in lst]
    centro = (min(todos) + max(todos)) / 2
    esq, dir_ = [], []
    for k in range(amostras):
        y = topo + vao * k / (amostras - 1)
        perto = [yy for yy in linhas if abs(yy - y) <= 1]
        xs = [x for yy in perto for x in linhas[yy]]
        if not xs:
            esq.append(0.0)
            dir_.append(0.0)
        else:
            esq.append(centro - min(xs))
            dir_.append(max(xs) - centro)
    return esq, dir_


def capturar():
    linhas_rep = _corpo(os.path.join(ORIGINAIS, '%s_%d.png' % REPOUSO))
    r_topo, r_base, r_centros = _perfil(linhas_rep)
    r_alc = _alcance(linhas_rep)
    r_orelhas = _orelhas(linhas_rep)
    r_vaos = _vaos(linhas_rep)
    r_peso = _peso(linhas_rep)
    r_quadril = _quadril(linhas_rep)
    r_meia = _meia_largura(linhas_rep, AMOSTRAS)
    r_orelha_q = _orelha_caida(linhas_rep)

    saida = {
        '_origem': 'primeiro goblin (32x32), commit bf9f49e',
        '_amostras': AMOSTRAS,
        '_repouso': {'topo': r_topo, 'base': r_base,
                     'altura': r_base - r_topo},
        'acoes': {},
    }
    for acao, n in ACOES.items():
        quadros = []
        for i in range(n):
            linhas = _corpo(os.path.join(ORIGINAIS, f'{acao}_{i}.png'))
            topo, base, centros = _perfil(linhas)
            alc = _alcance(linhas)
            # Vertical: o topo e a base andaram cada um o seu tanto, e no
            # meio o corpo acompanha os dois proporcionalmente. E assim
            # que um corpo que agacha se comporta — a cabeca desce muito,
            # o quadril pouco, o pe nada.
            d_topo = topo - r_topo
            d_base = base - r_base
            dy = [d_topo + (d_base - d_topo) * k / (AMOSTRAS - 1)
                  for k in range(AMOSTRAS)]
            dx = [centros[k] - r_centros[k] for k in range(AMOSTRAS)]
            # Suaviza o campo horizontal. Sem isso a ORELHA manda no
            # resultado: ela e o unico desenho na primeira linha do
            # corpo, tem meia duzia de pixels e balanca sozinha, entao o
            # "centro" daquela linha pula 3 px e, na hora de aplicar, a
            # cabeca inteira iria atras da orelha. A media movel devolve
            # o que interessa, que e a inclinacao do corpo.
            # Raio 2, e tem de ser. Medindo o CENTRO DE MASSA do goblin
            # original quadro a quadro, ele anda 0,12 px de lado no
            # parado e 0,17 na corrida: o corpo dele praticamente nao
            # inclina. O que o centro de cada LINHA mostra e o membro
            # daquela linha esticando — ler isso como inclinacao do
            # corpo (ja foi tentado, com raio 1) faz o goblin inteiro
            # tremer de lado 1 px de tela a cada quadro. O que troca de
            # lado e a PERNA, e isso e medido a parte, em _peso().
            dx = _suaviza(dx, 2)
            quadros.append({
                'dx': [round(v, 3) for v in dx],
                'dy': [round(v, 3) for v in dy],
                # ponta de cada membro, em relacao ao quadro parado
                'alcance': {k: alc[k] - r_alc[k] for k in r_alc},
                # quanto as duas orelhas abriram (ou fecharam) de largura
                'orelhas': _orelhas(linhas) - r_orelhas,
                # quanto os dois bracos / as duas pernas abriram
                'vao': {k: v - r_vaos[k] for k, v in _vaos(linhas).items()},
                # para que lado as pernas foram (troca de peso)
                'peso': round(_peso(linhas) - r_peso, 3),
                # bacia girando: desnivel entre os dois pes
                'quadril': _quadril(linhas) - r_quadril,
                # de cada lado, por altura: o que o membro daquela
                # altura abriu em relacao ao quadro parado
                'meia': {
                    'esq': [round(a - b, 3)
                            for a, b in zip(_meia_largura(linhas,
                                                          AMOSTRAS)[0],
                                            r_meia[0])],
                    'dir': [round(a - b, 3)
                            for a, b in zip(_meia_largura(linhas,
                                                          AMOSTRAS)[1],
                                            r_meia[1])],
                },
                # uma orelha caindo: desnivel entre as duas pontas
                'orelha_cai': _orelha_caida(linhas) - r_orelha_q,
            })
        saida['acoes'][acao] = quadros
    return saida


def main():
    dados = capturar()
    with open(SAIDA, 'w') as f:
        json.dump(dados, f, indent=1)
    print(f'OK -> {os.path.relpath(SAIDA, RAIZ)}')
    for acao, quadros in dados['acoes'].items():
        amp_x = max(max(abs(v) for v in q['dx']) for q in quadros)
        amp_y = max(max(abs(v) for v in q['dy']) for q in quadros)
        alc = max(max(abs(v) for v in q['alcance'].values())
                  for q in quadros)
        print(f'  {acao:7} {len(quadros):2d} quadros · corpo anda ate '
              f'{amp_x:.1f} px de lado e {amp_y:.1f} na vertical · '
              f'as pontas esticam ate {alc} px (tela de 32)')


if __name__ == '__main__':
    main()
