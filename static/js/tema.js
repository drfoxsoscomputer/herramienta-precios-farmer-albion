// tema.js — Tokens de color Tailwind del TEMA ALBION GLASS.
// Fuente única para TODAS las plantillas (antes estaba duplicado en
// base.html, qr_solo.html y launcher.html).
// Espejos sincronizados: static/css/tema.css y tema.py.
tailwind.config = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        oro:   { DEFAULT: '#c9a256', claro: '#e8b84a', brillo: '#f5d576' },
        bronce: '#8a6a3a',
        ambar: '#e8a545',
        fondo: '#1a1410',
        panel: '#241c16',
        borde: '#3a2a24',
      },
    },
  },
};

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
