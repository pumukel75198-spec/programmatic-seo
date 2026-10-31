#!/usr/bin/env node
/**
 * send-newsletter.mjs
 *
 * Vollautomatischer Newsletter-Versand über die MailerLite-Campaign-API.
 *
 * Ablauf:
 *   1. Neue Insights, APIs und Workflows seit dem letzten Versand ermitteln
 *      (State: `src/data/newsletter-state.json`).
 *   2. Eine responsive HTML-E-Mail bauen.
 *   3. Campaign in MailerLite anlegen und sofort versenden.
 *   4. State aktualisieren, damit nichts doppelt verschickt wird.
 *
 * Ohne neue Inhalte oder ohne `MAILERLITE_API_KEY` beendet sich das Script
 * sauber mit Exit-Code 0 – die GitHub Action schlägt nicht fehl.
 *
 * Verwendung:
 *   node scripts/send-newsletter.mjs
 *   node scripts/send-newsletter.mjs --dry-run
 *
 * Benötigt:
 *   MAILERLITE_API_KEY
 *   MAILERLITE_GROUP_ID
 *   MAILERLITE_FROM_EMAIL   (verifizierte Absenderadresse)
 *   MAILERLITE_FROM_NAME    (optional)
 *   SITE_URL                (optional, Default https://flowmatrix.dev)
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const dataDir = join(root, "src", "data");
const statePath = join(dataDir, "newsletter-state.json");

const dryRun = process.argv.includes("--dry-run");
const siteUrl = (process.env.SITE_URL ?? "https://flowmatrix.dev").replace(/\/$/, "");

const MAX_INSIGHTS = 3;
const MAX_APIS = 4;
const MAX_WORKFLOWS = 4;

function readJson(name, fallback) {
  const path = join(dataDir, name);
  if (!existsSync(path)) return fallback;
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch (error) {
    console.warn(`⚠ ${name} konnte nicht gelesen werden: ${error.message}`);
    return fallback;
  }
}

function loadState() {
  if (!existsSync(statePath)) {
    return { sentSlugs: { insights: [], apis: [], workflows: [] }, lastSentAt: null };
  }
  try {
    const parsed = JSON.parse(readFileSync(statePath, "utf8"));
    return {
      sentSlugs: {
        insights: parsed.sentSlugs?.insights ?? [],
        apis: parsed.sentSlugs?.apis ?? [],
        workflows: parsed.sentSlugs?.workflows ?? [],
      },
      lastSentAt: parsed.lastSentAt ?? null,
    };
  } catch {
    return { sentSlugs: { insights: [], apis: [], workflows: [] }, lastSentAt: null };
  }
}

function saveState(state) {
  writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`, "utf8");
}

const AMP = "&" + "amp;";
const LT = "&" + "lt;";
const GT = "&" + "gt;";
const QUOT = "&" + "quot;";
const APOS = "&" + "#39;";

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, AMP)
    .replace(/</g, LT)
    .replace(/>/g, GT)
    .replace(/"/g, QUOT)
    .replace(/'/g, APOS);
}

function pickNew(items, sentSlugs, limit) {
  const sent = new Set(sentSlugs);
  // Neue Einträge werden ans Ende angehängt – von hinten nach vorne prüfen.
  const fresh = [];
  for (let index = items.length - 1; index >= 0 && fresh.length < limit; index -= 1) {
    const item = items[index];
    if (!item?.slug || sent.has(item.slug)) continue;
    fresh.push(item);
  }
  return fresh;
}

function buildHtml({ insights, apis, workflows }) {
  const card = (href, title, description, meta) => `
    <tr>
      <td style="padding:0 0 18px 0;">
        <a href="${escapeHtml(href)}" style="text-decoration:none;color:#0f172a;">
          <div style="border:1px solid #e2e8f0;border-radius:14px;padding:18px 20px;background:#ffffff;">
            ${meta ? `<div style="font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#64748b;margin-bottom:6px;">${escapeHtml(meta)}</div>` : ""}
            <div style="font-size:16px;font-weight:650;line-height:1.35;margin-bottom:6px;">${escapeHtml(title)}</div>
            <div style="font-size:13px;line-height:1.6;color:#475569;">${escapeHtml(description)}</div>
          </div>
        </a>
      </td>
    </tr>`;

  const section = (heading, rows) =>
    rows.length === 0
      ? ""
      : `
    <tr>
      <td style="padding:8px 0 12px 0;">
        <div style="font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#2563eb;">${escapeHtml(heading)}</div>
      </td>
    </tr>
    ${rows.join("")}`;

  const insightRows = insights.map((item) =>
    card(
      `${siteUrl}/insights/${item.slug}/`,
      item.title,
      item.excerpt,
      item.category
    )
  );
  const apiRows = apis.map((item) =>
    card(`${siteUrl}/en/apis/${item.slug}/`, item.title, item.description, item.category)
  );
  const workflowRows = workflows.map((item) =>
    card(
      `${siteUrl}/en/workflows/${item.slug}/`,
      item.title,
      item.description,
      item.category
    )
  );

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>FlowMatrix update</title>
  </head>
  <body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:28px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;">
            <tr>
              <td style="padding:0 0 20px 0;">
                <div style="font-size:20px;font-weight:750;color:#0f172a;">FlowMatrix</div>
                <div style="font-size:13px;color:#64748b;margin-top:4px;">New APIs, workflows and insights – automatically curated.</div>
              </td>
            </tr>
            ${section("Latest insights", insightRows)}
            ${section("New APIs", apiRows)}
            ${section("New workflows", workflowRows)}
            <tr>
              <td style="padding:8px 0 0 0;">
                <a href="${siteUrl}" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;font-weight:650;font-size:14px;padding:12px 20px;border-radius:10px;">Explore FlowMatrix</a>
              </td>
            </tr>
            <tr>
              <td style="padding:24px 0 0 0;font-size:11px;line-height:1.6;color:#94a3b8;">
                You receive this email because you subscribed at flowmatrix.dev.
                <a href="{$unsubscribe}" style="color:#64748b;">Unsubscribe</a>.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>`;
}

async function mailerLite(path, options = {}) {
  const response = await fetch(`https://connect.mailerlite.com/api${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${process.env.MAILERLITE_API_KEY}`,
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(options.headers ?? {}),
    },
  });
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }
  if (!response.ok) {
    throw new Error(`MailerLite ${path} → ${response.status}: ${text.slice(0, 300)}`);
  }
  return data;
}

async function main() {
  const insights = readJson("insights.json", []);
  const apis = readJson("apis.json", []);
  const workflows = readJson("workflows.json", []);
  const state = loadState();

  const freshInsights = pickNew(insights, state.sentSlugs.insights, MAX_INSIGHTS);
  const freshApis = pickNew(apis, state.sentSlugs.apis, MAX_APIS);
  const freshWorkflows = pickNew(workflows, state.sentSlugs.workflows, MAX_WORKFLOWS);

  const total = freshInsights.length + freshApis.length + freshWorkflows.length;
  if (total === 0) {
    console.log("✔ Keine neuen Inhalte – kein Newsletter nötig.");
    return;
  }

  console.log(
    `▶ Newsletter: ${freshInsights.length} Insights, ${freshApis.length} APIs, ${freshWorkflows.length} Workflows`
  );

  const html = buildHtml({
    insights: freshInsights,
    apis: freshApis,
    workflows: freshWorkflows,
  });

  if (dryRun) {
    const cacheDir = join(root, ".cache");
    if (!existsSync(cacheDir)) mkdirSync(cacheDir, { recursive: true });
    const previewPath = join(cacheDir, "newsletter-preview.html");
    writeFileSync(previewPath, html, "utf8");
    console.log(`✔ Dry-run – Vorschau: ${previewPath}`);
    return;
  }

  if (!process.env.MAILERLITE_API_KEY) {
    console.warn("⚠ MAILERLITE_API_KEY fehlt – Versand übersprungen.");
    return;
  }
  if (!process.env.MAILERLITE_GROUP_ID) {
    console.warn("⚠ MAILERLITE_GROUP_ID fehlt – Versand übersprungen.");
    return;
  }
  if (!process.env.MAILERLITE_FROM_EMAIL) {
    console.warn("⚠ MAILERLITE_FROM_EMAIL fehlt – Versand übersprungen.");
    return;
  }

  const dateLabel = new Date().toISOString().slice(0, 10);
  const subject = `FlowMatrix update – ${dateLabel}`;

  const campaign = await mailerLite("/campaigns", {
    method: "POST",
    body: JSON.stringify({
      name: `FlowMatrix auto newsletter ${dateLabel}`,
      type: "regular",
      emails: [
        {
          subject,
          from: process.env.MAILERLITE_FROM_EMAIL,
          from_name: process.env.MAILERLITE_FROM_NAME ?? "FlowMatrix",
          reply_to: process.env.MAILERLITE_FROM_EMAIL,
        },
      ],
      groups: [String(process.env.MAILERLITE_GROUP_ID)],
      content: html,
    }),
  });

  const campaignId = campaign?.data?.id;
  if (!campaignId) {
    throw new Error("MailerLite hat keine Campaign-ID zurückgegeben.");
  }

  await mailerLite(`/campaigns/${campaignId}/schedule`, {
    method: "POST",
    body: JSON.stringify({ delivery: "instant" }),
  });

  console.log(`✔ Newsletter ${campaignId} wurde versendet.`);

  state.sentSlugs.insights.push(...freshInsights.map((item) => item.slug));
  state.sentSlugs.apis.push(...freshApis.map((item) => item.slug));
  state.sentSlugs.workflows.push(...freshWorkflows.map((item) => item.slug));
  state.lastSentAt = new Date().toISOString();
  saveState(state);
}

main().catch((error) => {
  console.error(`✖ ${error.message}`);
  process.exit(1);
});
