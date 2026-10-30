// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';

/** @type {string[]} */
const locales = [
  'en',
  'de',
  'fr',
  'es',
  'it',
  'pt',
  'nl',
  'pl',
  'sv',
  'tr',
  'ja',
  'zh',
];

// https://astro.build/config
export default defineConfig({
  // Static export: generates plain HTML/CSS/JS in ./dist
  output: 'static',

  // Production domain – used for canonical URLs and the sitemap.
  site: 'https://flowmatrix.dev',

  i18n: {
    defaultLocale: 'en',
    locales,
    routing: {
      prefixDefaultLocale: true,
      redirectToDefaultLocale: true,
    },
  },

  // Legacy paths without a locale prefix -> default locale (English).
  redirects: {
    '/apis': '/en/apis',
    '/alternatives': '/en/alternatives',
    '/workflows': '/en/workflows',
    '/imprint': '/en/imprint',
    '/privacy': '/en/privacy',
  },

  integrations: [
    sitemap({
      filter: (page) => !page.includes('/404'),
      i18n: {
        defaultLocale: 'en',
        locales: {
          en: 'en-US',
          de: 'de-DE',
          fr: 'fr-FR',
          es: 'es-ES',
          it: 'it-IT',
          pt: 'pt-PT',
          nl: 'nl-NL',
          pl: 'pl-PL',
          sv: 'sv-SE',
          tr: 'tr-TR',
          ja: 'ja-JP',
          zh: 'zh-CN',
        },
      },
    }),
  ],

  vite: {
    plugins: [tailwindcss()],
  },
});
