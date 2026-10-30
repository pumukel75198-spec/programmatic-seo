// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';

/** @type {string[]} */
const locales = ['en', 'de'];

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
      // Non-localized pages (e.g. /insights/*) exist only once. Do not emit
      // /de/... alternates for them in the sitemap, otherwise crawlers see
      // hreflang targets that 404.
      serialize(item) {
        if (item.url.includes('/insights/')) {
          return { ...item, links: [] };
        }
        return item;
      },
      i18n: {
        defaultLocale: 'en',
        locales: {
          en: 'en-US',
          de: 'de-DE',
        },
      },
    }),
  ],

  vite: {
    plugins: [tailwindcss()],
  },
});
