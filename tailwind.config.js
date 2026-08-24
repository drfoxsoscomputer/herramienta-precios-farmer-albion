// tailwind.config.js — Espejo de static/js/tema.js (tokens del TEMA ALBION GLASS).
// Solo lo usa el CLI para compilar static/css/tailwind.css UNA vez.
// La web NO carga Tailwind por CDN: el css compilado viaja dentro del paquete.
module.exports = {
  darkMode: 'class',
  content: ['./templates/**/*.html'],
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
