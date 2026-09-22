// ============================================================
// loader.js — Mini sistema de módulos (estilo CommonJS)
//
// Cada arquivo em js/ é escrito como um módulo puro: usa
// `require('outro.js')` e `module.exports = {...}`. Este loader
// busca os arquivos listados em js/_order.json, embrulha cada um
// numa função (module, exports, require) e só então roda main.js.
//
// Por que não ES Modules? Porque o mesmo código precisa funcionar
// nos dois cenários do projeto:
//   • desenvolvimento  → servido por HTTP (python3 -m http.server)
//   • build single-file → tudo embutido, aberto direto do disco
// No build, tools/build_singlefile.py já embute os módulos via
// __define() — a API __require é exatamente a mesma.
// ============================================================
var __modules = {};
var __cache = {};

function __define(name, factory) {
  __modules[name] = factory;
}

function __require(name) {
  if (!__cache[name]) {
    if (!__modules[name]) throw new Error('[loader] módulo não encontrado: ' + name);
    var m = { exports: {} };
    __cache[name] = m;            // registra antes de executar (permite ciclos)
    __modules[name](m, m.exports, __require);
  }
  return __cache[name].exports;
}

// ---------- Boot em modo desenvolvimento ----------
(async function bootDev() {
  // Se os módulos já vieram embutidos (build single-file), não há o que buscar.
  if (Object.keys(__modules).length) return;

  try {
    const order = await fetch('js/_order.json').then((r) => r.json());
    const sources = await Promise.all(
      order.map((n) => fetch('js/' + n).then((r) => r.text()))
    );

    order.forEach((name, i) => {
      // sourceURL faz o DevTools mostrar "js/village.js" no lugar de "VM123"
      const code = sources[i] + '\n//# sourceURL=js/' + name;
      __modules[name] = new Function('module', 'exports', 'require', code);
    });

    __require('main.js');
  } catch (e) {
    console.error('[loader] falha ao carregar os módulos:', e);
    document.body.innerHTML =
      '<pre style="color:#f88;padding:20px;font:12px monospace">'
      + '[loader] erro ao iniciar o jogo:\n' + (e && e.message)
      + '\n\nSirva a pasta por HTTP:  python3 -m http.server 8080</pre>';
  }
})();
