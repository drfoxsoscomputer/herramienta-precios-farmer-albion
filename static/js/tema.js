// tema.js — Utilidades globales de la web del TEMA ALBION GLASS.
// Los tokens de color Tailwind viven ahora en tailwind.config.js (los
// compila el CLI a static/css/tailwind.css: la web no usa CDN).
// Espejos sincronizados: static/css/tema.css y tema.py.

// Recarga con teclado (F5 / Ctrl+R / Ctrl+Shift+R): la ventana de
// escritorio (pywebview/WebView2) no las cablea por defecto. El
// service worker es network-first, así que recargar trae contenido
// fresco cuando hay red.
window.addEventListener('keydown', (e) => {
  const esF5 = e.key === 'F5';
  const esCtrlR = (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'r';
  if (esF5 || esCtrlR) {
    e.preventDefault();
    location.reload();
  }
});
