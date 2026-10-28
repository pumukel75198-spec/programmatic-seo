import { languages, translations, type TranslationKey } from "./ui";

export const defaultLocale = "en";
export const localeCodes: string[] = languages.map((lang) => lang.code);

export function isLocale(value: string | undefined): value is string {
  return !!value && localeCodes.includes(value);
}

export function getLocale(value: string | undefined): string {
  return isLocale(value) ? value : defaultLocale;
}

/** Translate a UI key for a given locale. */
export function t(lang: string, key: TranslationKey): string {
  return translations[lang]?.[key] ?? translations.en[key];
}

/** Build a localized path, e.g. localizedPath("de", "/apis") -> "/de/apis". */
export function localizedPath(lang: string, path = "/"): string {
  const clean = path.startsWith("/") ? path : `/${path}`;
  if (clean === "/") return `/${lang}/`;
  return `/${lang}${clean}`;
}

/** Replace the locale prefix of the current path. */
export function switchLocalePath(
  currentPath: string,
  targetLang: string
): string {
  const parts = currentPath.split("/").filter(Boolean);
  if (parts.length > 0 && isLocale(parts[0])) {
    parts[0] = targetLang;
  } else {
    parts.unshift(targetLang);
  }
  return `/${parts.join("/")}/`;
}

/** Strip the locale prefix from a path. */
export function pathWithoutLocale(currentPath: string): string {
  const parts = currentPath.split("/").filter(Boolean);
  if (parts.length > 0 && isLocale(parts[0])) {
    parts.shift();
  }
  return parts.length ? `/${parts.join("/")}/` : "/";
}
