// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  // Statischer Export: erzeugt reine HTML/CSS/JS-Dateien in ./dist
  output: 'static',

  // Passe diese URL auf deine Produktions-Domain an (wichtig für Canonical-URLs & Sitemap).
  site: 'https://example.com',

  integrations: [
    sitemap({
      // 404-Seite nicht in die Sitemap aufnehmen
      filter: (page) => !page.includes('/404'),
    }),
  ],

  vite: {
    plugins: [tailwindcss()]
  }
});
