"""Dez versoes do goblin para escolher a olho, lado a lado e animadas.

Todas partem do MESMO desenho: o que muda e so a paleta (quais tons
existem) e a forca da limpeza de chuvisco. Nenhuma versao mexe em
forma, pose ou animacao — essas ja foram aprovadas, e trocar duas
coisas ao mesmo tempo tornaria impossivel dizer qual delas melhorou.

    python3 tools/gif_versoes.py

Escreve art-source/goblin-v3/versoes/vNN.gif e um index.html.
"""
import importlib
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SAIDA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     'art-source', 'goblin-v3', 'versoes')
Z = 5
FUNDO = (26, 28, 24, 255)
TIRA = [('idle', 5), ('walk', 8), ('attack', 17), ('hurt', 17)]
QUADROS = 17

# ---------------------------------------------------------------- versoes
# 'cores'    sobrescreve simbolos da paleta
# 'passadas' quantas vezes a mediana roda sobre a arte (0 = arte crua)
VERSOES = [
    ('v01', 'A de agora: 4 verdes, limpeza normal', {}, 2),
    ('v02', 'Sem limpeza nenhuma (arte crua, so a paleta nova)', {}, 0),
    ('v03', 'Limpeza forte: mediana 4x', {}, 4),
    ('v04', 'Contorno preto, bem marcado', {'k': (20, 22, 21)}, 2),
    ('v05', 'Contorno verde-escuro (mais macio, sem borda preta)',
     {'k': (28, 72, 44)}, 2),
    ('v06', 'Exatamente os 3 verdes do original (menos detalhe)',
     {'e': (69, 165, 96), 'd': (69, 165, 96), 'n': (69, 165, 96),
      'j': (80, 189, 111), 'g': (80, 189, 111), 'l': (114, 210, 142)}, 2),
    ('v07', '5 verdes: degrade mais suave (mais detalhe)',
     {'e': (28, 78, 46), 'd': (50, 133, 78), 'n': (69, 165, 96),
      'j': (80, 189, 111), 'g': (97, 200, 124), 'l': (114, 210, 142)}, 2),
    ('v08', 'Mais contraste: sombra mais funda e luz mais forte',
     {'e': (22, 70, 42), 'd': (58, 150, 86), 'l': (140, 228, 165)}, 2),
    ('v09', 'Olho branco puro + contorno preto (cara mais legivel)',
     {'f': (246, 246, 255), 'w': (255, 255, 255), 'k': (20, 22, 21)}, 2),
    ('v10', 'Pele e pano mais quentes (goblin mais terroso)',
     {'e': (52, 104, 50), 'd': (84, 162, 84), 'n': (84, 162, 84),
      'j': (99, 186, 96), 'g': (99, 186, 96), 'l': (132, 208, 124),
      'B': (84, 54, 30), 'b': (116, 78, 50), 'h': (158, 112, 72)}, 2),
]


def _aplica(cores, passadas):
    """Recarrega o rig do zero e devolve o modulo de animacao pronto.

    Recarregar e preciso: as pecas limpas e a cara sao montadas na
    importacao, entao mudar a paleta depois nao refaria nada.
    """
    import goblin_rig as R
    importlib.reload(R)
    for simbolo, rgb in cores.items():
        R.C[simbolo] = tuple(rgb) + (255,)
    rosto = {(x, y) for cel in R.FACE_CELLS.values() for (x, y) in cel}
    cru = {'head': R.HEAD, 'torso': R.TORSO, 'arm_l': R.ARM_L,
           'arm_r': R.ARM_R, 'leg_l': R.LEG_L, 'leg_r': R.LEG_R}
    for nome, arte in cru.items():
        prot = rosto if nome == 'head' else ()
        R.DEFAULT_PART[nome] = (R.tira_chuvisco(arte, prot, passadas)
                                if passadas else [list(l) for l in arte])
    import goblin_anim as A
    importlib.reload(A)
    return A


def gif(nome, cores, passadas):
    A = _aplica(cores, passadas)
    tiras = {acao: A.render_action(acao) for acao, _ in TIRA}
    lado = 64 * Z
    paginas = []
    for i in range(QUADROS):
        pag = Image.new('RGBA', (len(TIRA) * lado, lado), FUNDO)
        for col, (acao, n) in enumerate(TIRA):
            im = tiras[acao][i % n].convert('RGBA')
            pag.alpha_composite(im.resize((lado, lado), Image.NEAREST),
                                (col * lado, 0))
        paginas.append(pag.convert('RGB').convert(
            'P', palette=Image.ADAPTIVE, colors=64))
    destino = os.path.join(SAIDA, nome + '.gif')
    paginas[0].save(destino, save_all=True, append_images=paginas[1:],
                    duration=120, loop=0, optimize=True)
    return destino


def main():
    os.makedirs(SAIDA, exist_ok=True)
    for nome, titulo, cores, passadas in VERSOES:
        caminho = gif(nome, cores, passadas)
        print(nome, titulo, os.path.getsize(caminho) // 1024, 'kB')
    blocos = '\n'.join(
        f'''  <figure>
    <figcaption><b>{nome.upper()}</b> — {titulo}</figcaption>
    <img src="{nome}.gif" alt="{nome}">
  </figure>''' for nome, titulo, _, _ in VERSOES)
    html = f'''<!doctype html>
<meta charset="utf-8">
<title>Goblin — 10 versoes</title>
<style>
 body {{ background:#15170f; color:#e8e4d0; font:15px/1.5 monospace;
        margin:0; padding:24px 16px; }}
 h1 {{ font-size:20px; margin:0 0 4px; }}
 p.ajuda {{ color:#9aa08a; margin:0 0 20px; }}
 figure {{ margin:0 0 26px; }}
 figcaption {{ margin-bottom:6px; }}
 img {{ width:100%; max-width:1280px; image-rendering:pixelated;
        border:1px solid #2c3024; background:#1a1c18; display:block; }}
</style>
<h1>Goblin — 10 versoes</h1>
<p class="ajuda">Colunas: parado · andando · batendo · levando pancada.
Diga o numero da que ficou melhor.</p>
{blocos}
'''
    with open(os.path.join(SAIDA, 'index.html'), 'w') as fh:
        fh.write(html)


if __name__ == '__main__':
    main()
