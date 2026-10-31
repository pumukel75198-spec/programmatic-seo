/**
 * Zentrale Monetarisierungs-Konfiguration.
 *
 * Alle Checkout-URLs laufen durch `normalizeCheckoutUrl`, damit
 * Platzhalter (z. B. aus Dokumentation/Kopiervorlagen) niemals als echter
 * Kauf-Link gerendert werden. Das schützt vor toten Buttons und falschen
 * Lemon-Squeezy-Versprechen (E-E-A-T / Vertrauen).
 */

const PLACEHOLDER_MARKERS = [
  "your-store.lemonsqueezy.com",
  "your_store",
  "your-",
  "your_",
  "xxxxxxxx-",
  "variant_id",
  "checkout/buy/your",
];

/** Liefert die URL nur zurück, wenn sie wie ein echter Checkout aussieht. */
export function normalizeCheckoutUrl(raw?: string | null): string {
  const value = (raw ?? "").trim();
  if (!value) return "";
  const lower = value.toLowerCase();
  if (PLACEHOLDER_MARKERS.some((marker) => lower.includes(marker))) {
    return "";
  }
  return value;
}

/** Checkout für das 4,99 € Premium-Workflow-PDF. */
export function resolveWorkflowCheckout(explicit?: string | null): string {
  return normalizeCheckoutUrl(
    explicit ??
      import.meta.env.PUBLIC_LEMON_WORKFLOW_CHECKOUT_URL ??
      import.meta.env.PUBLIC_LEMON_CHECKOUT_URL
  );
}

/** Checkout für das 19,99 € Python-Starter-Skript. */
export function resolveScriptCheckout(explicit?: string | null): string {
  return normalizeCheckoutUrl(
    explicit ??
      import.meta.env.PUBLIC_LEMON_SCRIPT_CHECKOUT_URL ??
      import.meta.env.PUBLIC_LEMON_CHECKOUT_URL
  );
}

/** Checkout für das FlowMatrix Playbook (Insights-Seite). */
export function resolvePlaybookCheckout(): string {
  return normalizeCheckoutUrl(
    import.meta.env.PUBLIC_LEMON_PLAYBOOK_CHECKOUT_URL ??
      import.meta.env.PUBLIC_LEMON_CHECKOUT_URL
  );
}

/** Basis-URL des Download-Gate-Workers (ohne abschließenden Slash). */
export function resolveDownloadGate(): string {
  return (import.meta.env.PUBLIC_DOWNLOAD_GATE_URL ?? "")
    .trim()
    .replace(/\/$/, "");
}
