#!/usr/bin/env node
/**
 * check-pdf-quality.mjs
 *
 * Selbstheilendes Qualitäts-Gate für alle Workflow-PDFs in `public/downloads/`.
 *
 * Ablauf:
 *   1. Prüfen: Einfachheit, Erklärqualität, Quellendeckung, Links,
 *      Halluzinationen und technische Integrität.
 *   2. Korrigieren: Sichere, deterministische Fehler werden automatisch in
 *      `src/data/workflows.json` behoben (Whitespace, fehlende Satzenden,
 *      Duplikate, Platzhalter-Domains, „100 %“, Junk-Werte).
 *   3. Neu erzeugen: Betroffene PDFs werden mit den korrigierten Daten neu
 *      generiert.
 *   4. Erneut prüfen: Erst wenn alles sauber ist, endet das Skript mit 0.
 *
 * Nicht automatisch korrigierbar sind inhaltliche Lücken (zu wenige Schritte,
 * fehlende Erklärungen, erfundene Fakten). Dann bricht das Gate mit einer
 * präzisen Meldung ab, statt still ein schlechtes PDF auszuliefern.
 *
 * Automatisch ausgeführt:
 *   • am Ende von `scripts/generate-pdfs.mjs`
 *   • über `npm run build` (prebuild → generate-pdfs)
 *
 * Manuell:
 *   node scripts/check-pdf-quality.mjs            # nur prüfen
 *   node scripts/check-pdf-quality.mjs --fix      # prüfen + korrigieren + neu erzeugen
 *   node scripts/check-pdf-quality.mjs --strict   # Warnungen blockieren ebenfalls
 *   node scripts/check-pdf-quality.mjs --only=mein-workflow-slug
 */

import { readFile, writeFile, access } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { PDFParse } from "pdf-parse";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const root = join(__dirname, "..");

const workflowsFile = join(root, "src", "data", "workflows.json");
const partnerFile = join(root, "src", "data", "partner.json");
const monetizationFile = join(root, "src", "data", "monetization.json");
const pdfDir = process.env.PDF_OUTPUT_DIR
  ? resolve(root, process.env.PDF_OUTPUT_DIR)
  : join(root, "private", "downloads");

const isMain = process.argv[1]
  ? resolve(process.argv[1]) === resolve(__filename)
  : false;

/* --------------------------------------------------------------------------
 * Grenzwerte – bewusst nah an den heutigen, gut lesbaren PDFs.
 * ------------------------------------------------------------------------ */
const LIMITS = {
  minTextChars: 800,
  minPages: 4,

  maxSentenceWords: 32,
  warnSentenceWords: 24,
  maxAverageSentenceWords: 16,
  maxLongSentenceRatio: 0.12,

  minSteps: 3,
  minDescriptionChars: 25,
  maxDescriptionChars: 400,
  maxDescriptionWords: 40,

  minStepTitleWords: 2,
  maxStepTitleWords: 14,
  maxStepTitleChars: 90,
  minActions: 3,
  minActionWords: 3,
  maxActionWords: 20,
  maxActionChars: 200,
  minChecklistItems: 2,
  minChecklistWords: 2,
  maxChecklistWords: 18,
  maxChecklistChars: 100,
  minResultChars: 10,
  maxResultChars: 220,
  maxResultWords: 28,
};

const c = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  cyan: "\x1b[36m",
};

/* --------------------------------------------------------------------------
 * Text-Helfer
 * ------------------------------------------------------------------------ */
const normalize = (value) =>
  String(value ?? "")
    .replace(/\s+/g, " ")
    .trim();

const lower = (value) => normalize(value).toLowerCase();

const compact = (value) =>
  String(value ?? "")
    .replace(/\s+/g, "")
    .toLowerCase();

const matchNormalize = (value) =>
  normalize(value)
    .replace(/-\s+/g, "-")
    .replace(/\/\s+/g, "/")
    .replace(/\s+([.,;:!?])/g, "$1")
    .toLowerCase();

const truncate = (value, max = 100) => {
  const text = normalize(value);
  return text.length > max ? `${text.slice(0, max)}…` : text;
};

const wordCount = (value) => {
  const text = normalize(value);
  return text ? text.split(/\s+/).length : 0;
};

const countOccurrences = (haystack, needle) => {
  if (!needle) return 0;
  let count = 0;
  let index = 0;
  while ((index = haystack.indexOf(needle, index)) !== -1) {
    count += 1;
    index += needle.length;
  }
  return count;
};

function splitSentences(value) {
  const text = normalize(value);
  if (!text) return [];

  const protectedText = text
    .replace(
      /\b(?:z|d|u|o)\.\s?B\.|\b(?:bzw|ca|inkl|zzgl|Nr|Dr|etc|vs)\./gi,
      (match) => match.replace(/\./g, "·")
    )
    .replace(/https?:\/\/[^\s]+/g, (url) => url.replace(/[.!?]+$/g, "·"));

  return protectedText
    .split(/(?<=[.!?])\s+/)
    .map((sentence) => sentence.replace(/·/g, ".").trim())
    .filter(Boolean);
}

/* --------------------------------------------------------------------------
 * URL-Helfer
 * ------------------------------------------------------------------------ */
function canonicalUrl(value) {
  try {
    const url = new URL(String(value).replace(/[),.;'"\]]+$/g, ""));
    url.hash = "";
    const path = url.pathname.replace(/\/+$/, "");
    return lower(`${url.protocol}//${url.host}${path}${url.search}`);
  } catch {
    return null;
  }
}

function collectUrlsFromValue(value, target) {
  if (typeof value === "string") {
    for (const match of value.matchAll(/https?:\/\/[^\s"'<>)]+/g)) {
      target.add(match[0]);
    }
    return;
  }
  if (Array.isArray(value)) {
    for (const item of value) collectUrlsFromValue(item, target);
    return;
  }
  if (value && typeof value === "object") {
    for (const item of Object.values(value)) collectUrlsFromValue(item, target);
  }
}

function buildAllowedUrls(workflows, partner, monetization) {
  const raw = new Set();
  collectUrlsFromValue(workflows, raw);
  collectUrlsFromValue(partner, raw);
  if (monetization?.checkoutUrl) raw.add(monetization.checkoutUrl);
  raw.add("https://flowmatrix.dev");
  // PDFs verlinken ohne Checkout-URL auf die jeweilige Workflow-Seite.
  for (const workflow of workflows) {
    if (workflow?.slug) {
      raw.add(`https://flowmatrix.dev/en/workflows/${workflow.slug}`);
    }
  }

  const allowed = new Set();
  for (const url of raw) {
    const canonical = canonicalUrl(url);
    if (canonical) allowed.add(canonical);
  }
  return allowed;
}

function extractRawUris(raw) {
  const uris = [];
  const regex = /\/URI\s*\(([^)]*)\)/g;
  let match;
  while ((match = regex.exec(raw)) !== null) {
    const decoded = match[1]
      .replace(/\\([()\\])/g, "$1")
      .replace(/\\n/g, "")
      .trim();
    if (decoded) uris.push(decoded);
  }
  return uris;
}

function extractTextUrls(text) {
  return [...text.matchAll(/https?:\/\/[^\s<>"')]+/g)].map((match) =>
    match[0].replace(/[),.;:'"\]]+$/g, "")
  );
}

/* --------------------------------------------------------------------------
 * Halluzinations-Muster
 * ------------------------------------------------------------------------ */
const HALLUCINATION_PATTERNS = [
  ["Werbeversprechen „garantiert“", /\bgarantiert\b/i],
  ["unbelegte Prozentaussage „100 %“", /\b100\s*%/i],
  ["unbelegte Studie", /\b(?:studie|studien|forschung)\s+(?:zeigt|zeigen|beweist|belegt)\b/i],
  ["unbelegte Autorität", /\b(?:wissenschaftlich|offiziell)\s+(?:bewiesen|bestätigt|empfohlen)\b/i],
  ["Superlativ „Nr. 1“", /\bnr\.?\s*1\b/i],
  ["Superlativ „marktführend“", /\bmarktführ/i],
  ["Superlativ „beste Lösung“", /\bbeste[rn]?\s+l[öo]sung\b/i],
  ["unbelegte Zeitangabe „in wenigen Minuten“", /\bin\s+wenigen\s+minuten\b/i],
  ["unbelegte Kostenaussage „kostenlos“", /\bkostenlos\b/i],
  ["unbelegte Rechtsaussage „DSGVO-konform“", /\bdsgvo[-\s]?konform\b/i],
  ["unbelegte Zertifizierung", /\bzertifiziert\b/i],
  ["unbelegte Empfehlung „offiziell empfohlen“", /\boffiziell\s+empfohlen\b/i],
  ["unbelegter Test „getestet von“", /\bgetestet\s+von\b/i],
  ["Superlativ „führend/weltklasse/revolutionär“", /\b(?:führend|weltklasse|revolutionär)\b/i],
  ["Platzhalter-Domain", /\b(?:example\.(?:com|org|net)|localhost|127\.0\.0\.1|0\.0\.0\.0)\b/i],
  ["Platzhalter-Pfad", /\b(?:path\/to|your[-\s]?domain|ihre[-\s]?domain|deine[-\s]?domain)\b/i],
  ["Template-Platzhalter", /\{\{|\}\}|<[^>]*(?:insert|todo|placeholder|dein|ihr)[^>]*>/i],
  ["Junk „Lorem Ipsum“", /lorem\s+ipsum/i],
  ["Junk „TODO“", /\bTODO\b|\bT\s+O\s+D\s+O\b/i],
  ["Junk „TBD“", /\bT\s*B\s*D\b/i],
  ["Junk „undefined“", /\bundefined\b/i],
  ["Junk „NaN“", /\bNaN\b/],
  ["veralteter OpenAI-Endpoint /v1/engines", /api\.openai\.com\/v1\/engines\//i],
  ["veralteter OpenAI-Completions-Endpoint", /api\.openai\.com\/v1\/completions/i],
  ["veraltetes Modell „text-davinci“", /text-davinci/i],
  ["veraltetes Modell „gpt-3.5-turbo“", /gpt-3\.5-turbo/i],
  ["veralteter Befehl „npm init astro“", /npm init astro/i],
];

/* --------------------------------------------------------------------------
 * Datenprüfung: Einfachheit + Erklärqualität
 * ------------------------------------------------------------------------ */
function requireText(value, label, errors) {
  if (!normalize(value)) {
    errors.push(`${label} fehlt oder ist leer`);
    return false;
  }
  return true;
}

function normalizeStep(step) {
  if (typeof step === "string") {
    return {
      title: step,
      description: "",
      actions: [],
      checklist: [],
      expectedResult: "",
    };
  }
  return {
    title: step?.title ?? "",
    description: step?.description ?? "",
    actions: Array.isArray(step?.actions) ? step.actions : [],
    checklist: Array.isArray(step?.checklist) ? step.checklist : [],
    expectedResult: step?.expectedResult ?? "",
  };
}

function checkWorkflowData(workflow, partner, errors, warnings) {
  const slug = workflow.slug ?? "(ohne Slug)";
  const prefix = `Workflow „${slug}“`;

  requireText(workflow.slug, `${prefix}: Slug`, errors);
  requireText(workflow.title, `${prefix}: Titel`, errors);
  requireText(workflow.description, `${prefix}: Beschreibung`, errors);
  requireText(workflow.category, `${prefix}: Kategorie`, errors);
  requireText(workflow.details?.difficulty, `${prefix}: Schwierigkeit`, errors);
  requireText(workflow.details?.duration, `${prefix}: Dauer`, errors);
  requireText(workflow.details?.useCase, `${prefix}: Use Case`, errors);

  if (normalize(workflow.title).length > 90) {
    errors.push(`${prefix}: Titel ist zu lang (${normalize(workflow.title).length} Zeichen)`);
  }
  if (wordCount(workflow.title) > 14) {
    errors.push(`${prefix}: Titel hat zu viele Wörter (${wordCount(workflow.title)})`);
  }

  const description = normalize(workflow.description);
  if (description && description.length < 40) {
    errors.push(`${prefix}: Beschreibung ist zu kurz (${description.length} Zeichen)`);
  }
  if (description.length > 350) {
    errors.push(`${prefix}: Beschreibung ist zu lang (${description.length} Zeichen)`);
  }
  if (description && !/[.!?]$/.test(description)) {
    errors.push(`${prefix}: Beschreibung endet nicht mit einem vollständigen Satz`);
  }
  if (compact(description) === compact(workflow.title)) {
    errors.push(`${prefix}: Beschreibung wiederholt nur den Titel`);
  }

  const tools = Array.isArray(workflow.details?.tools)
    ? workflow.details.tools
    : [];
  if (tools.length === 0) {
    errors.push(`${prefix}: Keine Tools hinterlegt`);
  }
  const seenTools = new Set();
  for (const tool of tools) {
    if (!normalize(tool)) {
      errors.push(`${prefix}: Leerer Tool-Eintrag`);
      continue;
    }
    if (seenTools.has(compact(tool))) {
      warnings.push(`${prefix}: Tool doppelt aufgeführt: „${tool}“`);
    }
    seenTools.add(compact(tool));

    const entry = partner?.[tool];
    if (!entry) {
      errors.push(
        `${prefix}: Tool „${tool}“ fehlt in partner.json (PDF würde einen Fallback-Link erhalten)`
      );
      continue;
    }
    const href = entry.affiliateUrl || entry.url;
    if (!/^https:\/\//i.test(String(href ?? ""))) {
      errors.push(`${prefix}: Tool „${tool}“ hat keinen gültigen https-Link`);
    }
  }

  const steps = Array.isArray(workflow.details?.steps)
    ? workflow.details.steps.map(normalizeStep)
    : [];
  if (steps.length < LIMITS.minSteps) {
    errors.push(
      `${prefix}: Zu wenige Schritte (${steps.length}, mindestens ${LIMITS.minSteps} erwartet)`
    );
  }

  const seenTitles = new Map();
  const seenResults = new Map();
  const allSentences = [workflow.description, workflow.details?.useCase]
    .filter(Boolean)
    .flatMap(splitSentences);

  steps.forEach((step, index) => {
    const label = `${prefix}, Schritt ${index + 1}`;
    const title = normalize(step.title);

    if (!title) {
      errors.push(`${label}: Titel ist leer`);
    } else {
      if (title.length > LIMITS.maxStepTitleChars) {
        errors.push(`${label}: Titel ist zu lang (${title.length} Zeichen)`);
      }
      if (wordCount(title) < LIMITS.minStepTitleWords) {
        errors.push(`${label}: Titel ist zu kurz (${wordCount(title)} Wörter)`);
      }
      if (wordCount(title) > LIMITS.maxStepTitleWords) {
        errors.push(`${label}: Titel hat zu viele Wörter (${wordCount(title)})`);
      }
      if (!/^[A-ZÄÖÜ0-9]/.test(title)) {
        errors.push(`${label}: Titel beginnt nicht mit einem Großbuchstaben`);
      }
      const titleKey = compact(title);
      if (seenTitles.has(titleKey)) {
        errors.push(
          `${label}: Doppelter Schritt-Titel (auch Schritt ${seenTitles.get(titleKey) + 1})`
        );
      } else {
        seenTitles.set(titleKey, index);
      }
    }

    const stepDescription = normalize(step.description);
    if (!stepDescription) {
      errors.push(`${label}: Beschreibung fehlt`);
    } else {
      if (stepDescription.length < LIMITS.minDescriptionChars) {
        errors.push(
          `${label}: Beschreibung ist zu kurz (${stepDescription.length} Zeichen)`
        );
      }
      if (stepDescription.length > LIMITS.maxDescriptionChars) {
        errors.push(
          `${label}: Beschreibung ist zu lang (${stepDescription.length} Zeichen)`
        );
      }
      if (!/[.!?]$/.test(stepDescription)) {
        errors.push(`${label}: Beschreibung endet nicht mit einem vollständigen Satz`);
      }
      if (wordCount(stepDescription) > LIMITS.maxDescriptionWords) {
        errors.push(
          `${label}: Beschreibung hat zu viele Wörter (${wordCount(stepDescription)})`
        );
      }
      if (compact(stepDescription) === compact(title)) {
        errors.push(`${label}: Beschreibung wiederholt nur den Titel`);
      }
      allSentences.push(...splitSentences(stepDescription));
    }

    if (!Array.isArray(step.actions) || step.actions.length < LIMITS.minActions) {
      errors.push(
        `${label}: Mindestens ${LIMITS.minActions} konkrete Handlungsschritte erwartet`
      );
    } else {
      const seenActions = new Set();
      step.actions.forEach((action, actionIndex) => {
        const actionLabel = `${label}, Aktion ${actionIndex + 1}`;
        const text = normalize(action);
        if (!text) {
          errors.push(`${actionLabel}: Aktion ist leer`);
          return;
        }
        const words = wordCount(text);
        if (words < LIMITS.minActionWords) {
          errors.push(`${actionLabel}: Aktion ist zu kurz (${words} Wörter)`);
        }
        if (words > LIMITS.maxActionWords) {
          errors.push(`${actionLabel}: Aktion ist zu lang (${words} Wörter)`);
        }
        if (text.length > LIMITS.maxActionChars) {
          errors.push(`${actionLabel}: Aktion ist zu lang (${text.length} Zeichen)`);
        }
        if (!/^[A-ZÄÖÜ0-9]/.test(text)) {
          errors.push(`${actionLabel}: Aktion beginnt nicht mit einem Großbuchstaben`);
        }
        const key = compact(text);
        if (seenActions.has(key)) {
          errors.push(`${actionLabel}: Aktion ist im selben Schritt doppelt`);
        }
        seenActions.add(key);
        allSentences.push(...splitSentences(text));
      });
    }

    if (
      !Array.isArray(step.checklist) ||
      step.checklist.length < LIMITS.minChecklistItems
    ) {
      errors.push(
        `${label}: Mindestens ${LIMITS.minChecklistItems} Checklisten-Punkte erwartet`
      );
    } else {
      const seenChecks = new Set();
      step.checklist.forEach((item, itemIndex) => {
        const checkLabel = `${label}, Checkliste ${itemIndex + 1}`;
        const text = normalize(item);
        if (!text) {
          errors.push(`${checkLabel}: Eintrag ist leer`);
          return;
        }
        if (text.length > LIMITS.maxChecklistChars) {
          errors.push(`${checkLabel}: Eintrag ist zu lang (${text.length} Zeichen)`);
        }
        if (wordCount(text) < LIMITS.minChecklistWords) {
          errors.push(`${checkLabel}: Eintrag ist zu kurz (${wordCount(text)} Wörter)`);
        }
        if (wordCount(text) > LIMITS.maxChecklistWords) {
          errors.push(
            `${checkLabel}: Eintrag hat zu viele Wörter (${wordCount(text)})`
          );
        }
        const key = compact(text);
        if (seenChecks.has(key)) {
          errors.push(`${checkLabel}: Eintrag ist doppelt`);
        }
        seenChecks.add(key);
      });
    }

    const result = normalize(step.expectedResult);
    if (!result) {
      errors.push(`${label}: Erwartetes Ergebnis fehlt`);
    } else {
      if (result.length < LIMITS.minResultChars) {
        errors.push(`${label}: Ergebnis ist zu kurz (${result.length} Zeichen)`);
      }
      if (result.length > LIMITS.maxResultChars) {
        errors.push(`${label}: Ergebnis ist zu lang (${result.length} Zeichen)`);
      }
      if (!/[.!?]$/.test(result)) {
        errors.push(`${label}: Ergebnis endet nicht mit einem vollständigen Satz`);
      }
      if (wordCount(result) > LIMITS.maxResultWords) {
        errors.push(`${label}: Ergebnis hat zu viele Wörter (${wordCount(result)})`);
      }
      const key = compact(result);
      if (seenResults.has(key)) {
        warnings.push(
          `${label}: Ergebnis ist identisch mit Schritt ${seenResults.get(key) + 1}`
        );
      } else {
        seenResults.set(key, index);
      }
      allSentences.push(...splitSentences(result));
    }
  });

  // Wichtig: allSentences enthält bereits fertig zerlegte Sätze. Nicht erneut
  // zusammenkleben, sonst verschmelzen unpunktierte Aktionen mit dem Folgefeld.
  const sentences = allSentences;
  if (sentences.length > 0) {
    const lengths = sentences.map(wordCount);
    const average = lengths.reduce((sum, n) => sum + n, 0) / lengths.length;
    const longest = Math.max(...lengths);
    const longCount = lengths.filter((n) => n > LIMITS.warnSentenceWords).length;

    if (longest > LIMITS.maxSentenceWords) {
      errors.push(
        `${prefix}: Ein Satz ist zu lang (${longest} Wörter, maximal ${LIMITS.maxSentenceWords})`
      );
    } else if (longest > LIMITS.warnSentenceWords) {
      warnings.push(
        `${prefix}: Ein Satz ist lang (${longest} Wörter) – für einfache Sprache kürzen`
      );
    }
    if (average > LIMITS.maxAverageSentenceWords) {
      errors.push(
        `${prefix}: Durchschnittliche Satzlänge zu hoch (${average.toFixed(1)} Wörter, maximal ${LIMITS.maxAverageSentenceWords})`
      );
    }
    if (longCount / lengths.length > LIMITS.maxLongSentenceRatio) {
      warnings.push(
        `${prefix}: ${longCount} von ${lengths.length} Sätzen sind länger als ${LIMITS.warnSentenceWords} Wörter`
      );
    }
  }
}

/* --------------------------------------------------------------------------
 * PDF-Prüfung
 * ------------------------------------------------------------------------ */
async function extractText(buffer) {
  const parser = new PDFParse({ data: buffer });
  try {
    const result = await parser.getText();
    return result.text ?? "";
  } finally {
    await parser.destroy();
  }
}

function checkContains(text, needle, label, errors) {
  if (!needle) return;
  if (!matchNormalize(text).includes(matchNormalize(needle))) {
    errors.push(`${label} fehlt im PDF-Text: „${truncate(needle)}“`);
  }
}

function checkSections(workflow, text, errors) {
  const compactText = compact(text);
  const steps = Array.isArray(workflow.details?.steps)
    ? workflow.details.steps.map(normalizeStep)
    : [];

  const sections = [
    ["OVERVIEW", "overview"],
    ["STEP BY STEP", "stepbystep"],
    ["How to implement it", "howtoimplementit"],
    ["WHAT YOU NEED TO DO", "whatyouneedtodo"],
    ["CHECK AT THE END", "checkattheend"],
    ["RESULT", "result"],
    ["RECOMMENDED TOOLS & RESOURCES", "recommendedtools&resources"],
    ["What you use it for", "whatyouuseitfor"],
    ["Tools in this workflow", "toolsinthisworkflow"],
  ];

  for (const [label, needle] of sections) {
    if (!compactText.includes(needle)) {
      errors.push(`Pflichtabschnitt fehlt: „${label}“`);
    }
  }

  // Auf eine Index-basierte Reihenfolgeprüfung wird bewusst verzichtet:
  // PDF-Text wird objekt-, nicht seitenlinear extrahiert. Die Reihenfolge ist
  // durch den Generator festgelegt und wird über die Pflichtabschnitte und
  // die Anzahl der Schritt-Blöcke abgesichert.
  const actionBlocks = countOccurrences(compactText, "whatyouneedtodo");
  const checklistBlocks = countOccurrences(compactText, "checkattheend");
  const resultBlocks = countOccurrences(compactText, "result");

  if (actionBlocks < steps.length) {
    errors.push(
      `„DAS MUSST DU TUN“ fehlt für ${steps.length - actionBlocks} Schritt(e)`
    );
  }
  if (checklistBlocks < steps.length) {
    errors.push(
      `„PRÜFE AM ENDE“ fehlt für ${steps.length - checklistBlocks} Schritt(e)`
    );
  }
  if (resultBlocks < steps.length) {
    errors.push(`„ERGEBNIS“ fehlt für ${steps.length - resultBlocks} Schritt(e)`);
  }

  const pageNumbers = [...text.matchAll(/Page\s+(\d+)\s+of\s+(\d+)/g)].map(
    (match) => ({ page: Number(match[1]), total: Number(match[2]) })
  );

  if (pageNumbers.length === 0) {
    errors.push("Keine Seitenzahlen im PDF gefunden");
  } else {
    const total = pageNumbers[0].total;
    if (!pageNumbers.every((entry) => entry.total === total)) {
      errors.push("Seitenzahlen sind inkonsistent („Seite X von Y“)");
    }
    if (total < LIMITS.minPages) {
      errors.push(`PDF hat zu wenige Seiten (${total}, mindestens ${LIMITS.minPages})`);
    }
    const found = new Set(pageNumbers.map((entry) => entry.page));
    for (let page = 2; page <= total; page += 1) {
      if (!found.has(page)) {
        errors.push(`Seitenzahl für Seite ${page} fehlt`);
      }
    }
  }
}

function checkUrls(raw, text, workflow, partner, monetization, allowed, errors) {
  const rawUris = extractRawUris(raw);
  const textUrls = extractTextUrls(text);

  if (rawUris.length === 0) {
    errors.push("Keine klickbaren URLs (/URI) im PDF gefunden");
  }
  if (/http:\/\//i.test(text)) {
    errors.push("Unverschlüsselter http:-Link im PDF gefunden");
  }

  const checkUrl = (url, source) => {
    const canonical = canonicalUrl(url);
    if (!canonical) {
      errors.push(`${source}: Ungültige URL „${truncate(url)}“`);
      return;
    }
    if (allowed.has(canonical)) return;

    const asPrefix = [...allowed].some(
      (candidate) => candidate.startsWith(canonical) && canonical.length >= 20
    );
    if (asPrefix) return;

    errors.push(
      `${source}: URL ist nicht durch die Quelldaten gedeckt: „${truncate(url)}“`
    );
  };

  for (const url of rawUris) checkUrl(url, "Link");
  for (const url of textUrls) checkUrl(url, "Textlink");

  const rawLower = lower(raw);
  const textMatch = matchNormalize(text);

  const tools = Array.isArray(workflow.details?.tools)
    ? workflow.details.tools
    : [];
  for (const tool of tools) {
    const entry = partner?.[tool];
    const href = entry?.affiliateUrl || entry?.url;
    if (!href) continue;
    if (!rawLower.includes(lower(href)) && !textMatch.includes(matchNormalize(href))) {
      errors.push(`Tool-Link fehlt im PDF: „${tool}“ → ${href}`);
    }
  }

  const checkout =
    normalize(monetization?.checkoutUrl) ||
    `https://flowmatrix.dev/en/workflows/${workflow.slug}`;
  if (
    !rawLower.includes(lower(checkout)) &&
    !textMatch.includes(matchNormalize(checkout))
  ) {
    errors.push(`Checkout-/Workflow-Link fehlt im PDF: ${checkout}`);
  }
}

const GERMAN_TEXT_PATTERN =
  /\b(und|oder|aber|der|das|den|dem|des|ein|eine|einen|einem|einer|ist|sind|wird|werden|Sie|Ihre|Ihren|Ihrem|erstellen|speichern|öffnen|fügen|konfigurieren|überprüfen|senden|rufen|verbinden|installieren|richten|setzen|wählen|klicken|tragen|prüfen|aktualisieren|verwenden|nutzen|hinzu|anschließend|damit|für|mit|von|zu|im|auf|als|bei|nach|aus|durch|können|müssen|sollte|haben|nicht|auch|noch|nur|dann|wenn|dass|ob|wie|was|wer|wo|beim|zur|zum)\b/i;

/**
 * Stellt sicher, dass PDFs vollständig englisch sind – auch für zukünftige
 * Workflows. Bewusst konservative Wortliste, damit englische Begriffe wie
 * "die", "in" oder "hat" keine Fehlalarme auslösen.
 */
function checkEnglish(text, errors) {
  const match = text.match(GERMAN_TEXT_PATTERN);
  if (match) {
    errors.push(`PDF enthält deutschen Text: „${truncate(match[0], 40)}“`);
  }
  if (/[äöüß]/i.test(text)) {
    errors.push("PDF enthält deutsche Umlaute oder ß");
  }
}

function checkClaims(text, workflows, monetization, errors) {
  for (const [label, pattern] of HALLUCINATION_PATTERNS) {
    const match = text.match(pattern);
    if (match) {
      errors.push(
        `Halluzination/Versprechen gefunden (${label}): „${truncate(match[0], 60)}“`
      );
    }
  }

  const expectedPrice = compact(monetization?.price ?? "");
  const amounts = [
    ...text.matchAll(/(?:€\s*\d+[.,]\d{2}|\d+[.,]\d{2}\s*(?:€|EUR))/gi),
  ].map((match) => compact(match[0]).replace("eur", "€"));
  for (const amount of new Set(amounts)) {
    if (amount !== expectedPrice) {
      errors.push(
        `Unerwarteter Preis im PDF: „${amount}“ (erwartet: „${expectedPrice}“)`
      );
    }
  }
  if (expectedPrice && !compact(text).includes(expectedPrice)) {
    errors.push(`Preis „${monetization.price}“ fehlt im PDF-Text`);
  }

  const allowedPercents = new Set();
  const collectPercents = (value) => {
    if (typeof value === "string") {
      for (const match of value.matchAll(/\d+(?:[.,]\d+)?\s*%/g)) {
        allowedPercents.add(compact(match[0]));
      }
      return;
    }
    if (Array.isArray(value)) {
      value.forEach(collectPercents);
      return;
    }
    if (value && typeof value === "object") {
      Object.values(value).forEach(collectPercents);
    }
  };
  collectPercents(workflows);

  const percentMatches = [...text.matchAll(/\d+(?:[.,]\d+)?\s*%/g)].map((match) =>
    compact(match[0])
  );
  for (const percent of new Set(percentMatches)) {
    if (!allowedPercents.has(percent)) {
      errors.push(`Prozentangabe nicht durch Quelldaten gedeckt: „${percent}“`);
    }
  }

  const premiumText = lower(text).replace(/[-\s]+/g, " ");
  if (
    !premiumText.includes("premium pdf") &&
    !premiumText.includes("premium workflow")
  ) {
    errors.push('Hinweis „Premium-PDF“/„Premium-Workflow“ fehlt');
  }
}

async function checkPdf(workflow, partner, monetization, allowed, errors, warnings) {
  const fileName = `flowmatrix-${workflow.slug}.pdf`;
  const filePath = join(pdfDir, fileName);

  try {
    await access(filePath);
  } catch {
    errors.push(`PDF-Datei fehlt: ${filePath}`);
    return;
  }

  const buffer = await readFile(filePath);
  if (buffer.length < 1024) {
    errors.push(`PDF ist verdächtig klein (${buffer.length} Bytes)`);
  }

  const raw = buffer.toString("latin1");
  let text = "";
  try {
    text = await extractText(buffer);
  } catch (error) {
    errors.push(`PDF-Text konnte nicht extrahiert werden: ${error.message}`);
    return;
  }

  if (!normalize(text)) {
    errors.push("PDF enthält keinen extrahierbaren Text");
    return;
  }
  if (normalize(text).length < LIMITS.minTextChars) {
    errors.push(
      `PDF-Text ist zu kurz (${normalize(text).length} Zeichen, mindestens ${LIMITS.minTextChars})`
    );
  }

  checkContains(text, workflow.title, "Titel", errors);
  checkContains(text, workflow.description, "Beschreibung", errors);
  checkContains(text, workflow.category, "Kategorie", errors);
  checkContains(text, workflow.details?.difficulty, "Schwierigkeit", errors);
  checkContains(text, workflow.details?.duration, "Dauer", errors);
  checkContains(text, workflow.details?.useCase, "Use Case", errors);

  const steps = Array.isArray(workflow.details?.steps)
    ? workflow.details.steps.map(normalizeStep)
    : [];
  steps.forEach((step, index) => {
    checkContains(text, step.title, `Schritt ${index + 1} Titel`, errors);
    checkContains(text, step.description, `Schritt ${index + 1} Beschreibung`, errors);
    step.actions.forEach((action, actionIndex) => {
      checkContains(
        text,
        action,
        `Schritt ${index + 1} Aktion ${actionIndex + 1}`,
        errors
      );
    });
    step.checklist.forEach((item, itemIndex) => {
      checkContains(
        text,
        item,
        `Schritt ${index + 1} Checkliste ${itemIndex + 1}`,
        errors
      );
    });
    checkContains(text, step.expectedResult, `Schritt ${index + 1} Ergebnis`, errors);
  });

  const tools = Array.isArray(workflow.details?.tools)
    ? workflow.details.tools
    : [];
  for (const tool of tools) {
    checkContains(text, tool, `Tool „${tool}“`, errors);
  }

  checkSections(workflow, text, errors);
  checkUrls(raw, text, workflow, partner, monetization, allowed, errors);
  checkClaims(text, [workflow], monetization, errors);
  checkEnglish(text, errors);
}

/* --------------------------------------------------------------------------
 * Sichere Auto-Korrekturen
 * ------------------------------------------------------------------------ */
const TEXT_FIXES = [
  [
    /https?:\/\/(?:[\w-]+\.)*example\.(?:com|org|net)(?:\/[^\s,;)]*)?/gi,
    "deine eigene URL",
    "Platzhalter-Domain ersetzt",
  ],
  [
    /https?:\/\/localhost(?::\d+)?(?:\/[^\s,;)]*)?/gi,
    "deine lokale URL",
    "localhost-Link ersetzt",
  ],
  [/\bpath\/to\/[^\s,;)]+/gi, "dein Dateipfad", "Platzhalter-Pfad ersetzt"],
  [
    /\b(?:your|ihre|deine)[-\s]?domain\b/gi,
    "deine Domain",
    "Platzhalter-Domain ersetzt",
  ],
  [/\{\{[^}]*\}\}/g, "Wert", "Template-Platzhalter ersetzt"],
  [/\bundefined\b/gi, "nicht definiert", "„undefined“ ersetzt"],
  [/\bNaN\b/g, "nicht verfügbar", "„NaN“ ersetzt"],
  [/\b100\s*%/gi, "vollständig", "unbelegte „100 %“-Aussage ersetzt"],
];

function fixText(value, label, fixes) {
  if (typeof value !== "string") return value;

  let text = normalize(value);
  if (text !== value) {
    fixes.push(`${label}: Leerzeichen normalisiert`);
  }

  for (const [pattern, replacement, message] of TEXT_FIXES) {
    if (pattern.test(text)) {
      text = text.replace(pattern, replacement);
      fixes.push(`${label}: ${message}`);
    }
    pattern.lastIndex = 0;
  }

  return text;
}

function fixSentence(value, label, fixes) {
  let text = fixText(value, label, fixes);
  if (text && !/[.!?]$/.test(text)) {
    text = `${text}.`;
    fixes.push(`${label}: fehlendes Satzende ergänzt`);
  }
  return text;
}

function fixArray(values, label, fixes) {
  if (!Array.isArray(values)) return values;

  const seen = new Set();
  const result = [];
  values.forEach((value, index) => {
    const text = fixText(value, `${label} ${index + 1}`, fixes);
    const key = compact(text);
    if (!key) {
      fixes.push(`${label} ${index + 1}: leerer Eintrag entfernt`);
      return;
    }
    if (seen.has(key)) {
      fixes.push(`${label} ${index + 1}: Duplikat entfernt`);
      return;
    }
    seen.add(key);
    result.push(text);
  });
  return result;
}

export function applySafeFixes(workflows) {
  const fixed = structuredClone(workflows);
  const fixes = [];

  fixed.forEach((workflow, workflowIndex) => {
    const prefix = `Workflow „${workflow.slug ?? workflowIndex + 1}“`;

    workflow.title = fixText(workflow.title, `${prefix}: Titel`, fixes);
    workflow.description = fixSentence(
      workflow.description,
      `${prefix}: Beschreibung`,
      fixes
    );
    workflow.category = fixText(workflow.category, `${prefix}: Kategorie`, fixes);

    if (workflow.details) {
      workflow.details.difficulty = fixText(
        workflow.details.difficulty,
        `${prefix}: Schwierigkeit`,
        fixes
      );
      workflow.details.duration = fixText(
        workflow.details.duration,
        `${prefix}: Dauer`,
        fixes
      );
      workflow.details.useCase = fixSentence(
        workflow.details.useCase,
        `${prefix}: Use Case`,
        fixes
      );

      if (Array.isArray(workflow.details.tools)) {
        workflow.details.tools = fixArray(
          workflow.details.tools,
          `${prefix}: Tool`,
          fixes
        );
      }

      if (Array.isArray(workflow.details.steps)) {
        workflow.details.steps.forEach((step, stepIndex) => {
          if (!step || typeof step !== "object") return;
          const stepLabel = `${prefix}, Schritt ${stepIndex + 1}`;

          step.title = fixText(step.title, `${stepLabel}: Titel`, fixes);
          step.description = fixSentence(
            step.description,
            `${stepLabel}: Beschreibung`,
            fixes
          );
          step.actions = fixArray(
            step.actions,
            `${stepLabel}: Aktion`,
            fixes
          );
          step.checklist = fixArray(
            step.checklist,
            `${stepLabel}: Checkliste`,
            fixes
          );
          step.expectedResult = fixSentence(
            step.expectedResult,
            `${stepLabel}: Ergebnis`,
            fixes
          );
        });
      }
    }
  });

  return { workflows: fixed, fixes };
}

/* --------------------------------------------------------------------------
 * Gate + automatische Reparatur
 * ------------------------------------------------------------------------ */
export async function runQualityGate({
  workflows,
  partner,
  monetization,
  only = [],
  strict = false,
  quiet = false,
} = {}) {
  if (!Array.isArray(workflows) || workflows.length === 0) {
    console.error(`${c.red}${c.bold}✖ Keine Workflows zum Prüfen übergeben.${c.reset}`);
    return { ok: false, passed: 0, failed: 0, warnings: 0 };
  }
  if (!existsSync(pdfDir)) {
    console.error(`${c.red}✖ PDF-Verzeichnis fehlt: ${pdfDir}${c.reset}`);
    return { ok: false, passed: 0, failed: 0, warnings: 0 };
  }

  const onlySet = new Set(only.map((value) => String(value).trim()).filter(Boolean));
  const selected = onlySet.size
    ? workflows.filter(
        (workflow) =>
          onlySet.has(workflow.slug) || onlySet.has(`flowmatrix-${workflow.slug}.pdf`)
      )
    : workflows;

  if (selected.length === 0) {
    console.error(`${c.red}✖ Kein Workflow passt zu --only.${c.reset}`);
    return { ok: false, passed: 0, failed: 0, warnings: 0 };
  }

  const allowed = buildAllowedUrls(workflows, partner ?? {}, monetization ?? {});

  if (!quiet) {
    console.log(
      `${c.cyan}${c.bold}▶ PDF-Qualitätsprüfung: ${selected.length} PDFs${c.reset} ${c.dim}(${pdfDir})${c.reset}`
    );
  }

  let failed = 0;
  let passed = 0;
  let warningCount = 0;

  for (const workflow of selected) {
    const errors = [];
    const warnings = [];

    checkWorkflowData(workflow, partner ?? {}, errors, warnings);
    await checkPdf(workflow, partner ?? {}, monetization ?? {}, allowed, errors, warnings);

    const fileName = `flowmatrix-${workflow.slug}.pdf`;
    warningCount += warnings.length;

    if (errors.length === 0 && (!strict || warnings.length === 0)) {
      passed += 1;
      if (!quiet) {
        console.log(
          `  ${c.green}✓${c.reset} ${fileName}${
            warnings.length ? ` ${c.yellow}(${warnings.length} Hinweis(e))${c.reset}` : ""
          }`
        );
        for (const warning of warnings) {
          console.log(`      ${c.yellow}• ${warning}${c.reset}`);
        }
      }
      continue;
    }

    failed += 1;
    console.error(`  ${c.red}✖${c.reset} ${fileName}`);
    for (const error of errors) {
      console.error(`      ${c.red}• ${error}${c.reset}`);
    }
    for (const warning of warnings) {
      console.error(`      ${c.yellow}• ${warning}${c.reset}`);
    }
  }

  if (!quiet) console.log("");

  if (failed > 0) {
    console.error(
      `${c.red}${c.bold}✖ PDF-Qualitätsprüfung fehlgeschlagen: ${failed} von ${selected.length} PDFs nicht sauber.${c.reset}`
    );
    return { ok: false, passed, failed, warnings: warningCount };
  }

  if (!quiet) {
    console.log(
      `${c.green}${c.bold}✔ PDF-Qualitätsprüfung erfolgreich: ${passed} PDFs einfach erklärt, inhaltlich gedeckt und ohne Halluzinationen.${c.reset}` +
        (warningCount
          ? ` ${c.yellow}${warningCount} Hinweis(e) beachten.${c.reset}`
          : "")
    );
  }

  return { ok: true, passed, failed, warnings: warningCount };
}

/**
 * Prüft, korrigiert sichere Fehler, erzeugt die PDFs neu und prüft erneut.
 *
 * @param {object} options
 * @param {() => Promise<object>} options.loadData Liefert { workflows, partner, monetization }
 * @param {(data: object) => Promise<void>} [options.regenerate] Erzeugt die PDFs neu
 */
export async function ensurePdfQuality({
  loadData,
  regenerate,
  strict = false,
  quiet = false,
  only = [],
} = {}) {
  let data = await loadData();
  let result = await runQualityGate({ ...data, strict, quiet, only });

  if (result.ok) return result;
  if (process.env.PDF_SKIP_AUTO_FIX === "1") return result;

  const { workflows, fixes } = applySafeFixes(data.workflows);
  if (fixes.length === 0) {
    if (!quiet) {
      console.error(
        `${c.yellow}Keine sichere Auto-Korrektur möglich – bitte die obigen Punkte inhaltlich beheben.${c.reset}`
      );
    }
    return result;
  }

  if (!quiet) {
    console.log(
      `${c.cyan}${c.bold}▶ Auto-Korrektur: ${fixes.length} sichere Änderung(en)${c.reset}`
    );
  }
  for (const fix of fixes) {
    console.log(`  ${c.green}✓${c.reset} ${fix}`);
  }

  await writeFile(
    workflowsFile,
    `${JSON.stringify(workflows, null, 2)}\n`,
    "utf8"
  );

  data = await loadData();

  if (regenerate) {
    if (!quiet) {
      console.log(`${c.cyan}▶ Erzeuge betroffene PDFs mit korrigierten Daten neu …${c.reset}`);
    }
    await regenerate(data);
    data = await loadData();
  }

  if (!quiet) {
    console.log(`${c.cyan}▶ Prüfe nach der Korrektur erneut …${c.reset}`);
  }
  result = await runQualityGate({ ...data, strict, quiet, only });

  if (result.ok && !quiet) {
    console.log(`${c.green}${c.bold}✔ PDFs wurden automatisch korrigiert und sind sauber.${c.reset}`);
  }

  return result;
}

/* --------------------------------------------------------------------------
 * CLI
 * ------------------------------------------------------------------------ */
async function loadData() {
  for (const file of [workflowsFile, partnerFile, monetizationFile]) {
    if (!existsSync(file)) {
      throw new Error(`Datei nicht gefunden: ${file}`);
    }
  }

  const workflows = JSON.parse(await readFile(workflowsFile, "utf8"));
  const partner = JSON.parse(await readFile(partnerFile, "utf8"));
  const monetization = JSON.parse(await readFile(monetizationFile, "utf8"));

  if (!Array.isArray(workflows)) {
    throw new Error("workflows.json muss ein Array sein.");
  }

  monetization.checkoutUrl =
    process.env.PUBLIC_LEMON_WORKFLOW_CHECKOUT_URL?.trim() ||
    process.env.PUBLIC_LEMON_CHECKOUT_URL?.trim() ||
    monetization.checkoutUrl;

  return { workflows, partner, monetization };
}

async function main() {
  const args = process.argv.slice(2);
  const strict = args.includes("--strict");
  const quiet = args.includes("--quiet");
  const fix = args.includes("--fix");
  const only = args
    .filter((arg) => arg.startsWith("--only="))
    .map((arg) => arg.slice("--only=".length));

  const onlyFlagIndex = args.indexOf("--only");
  if (onlyFlagIndex !== -1 && args[onlyFlagIndex + 1]) {
    only.push(args[onlyFlagIndex + 1]);
  }

  if (fix) {
    const result = await ensurePdfQuality({
      loadData,
      regenerate: async (data) => {
        const { generateAllPdfs } = await import("./generate-pdfs.mjs");
        await generateAllPdfs({ ...data, quiet: true });
      },
      strict,
      quiet,
      only,
    });
    if (!result.ok) process.exit(1);
    return;
  }

  const data = await loadData();
  const result = await runQualityGate({ ...data, strict, quiet, only });
  if (!result.ok) process.exit(1);
}

if (isMain) {
  main().catch((error) => {
    console.error(`${c.red}${c.bold}✖ Qualitätsprüfung abgebrochen:${c.reset}`, error);
    process.exit(1);
  });
}
