// @ts-check
import { defineConfig } from 'astro/config';

import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  // Statischer Export: erzeugt reine HTML/CSS/JS-Dateien in ./dist
  output: 'static',

  // Passe diese URL auf deine Produktions-Domain an (wichtig für Canonical-URLs & Sitemap).
  site: 'https://example.com',

  vite: {
    plugins: [tailwindcss()]
  }
});
