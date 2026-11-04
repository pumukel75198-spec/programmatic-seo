import { describe, it, expect, vi, afterEach } from "vitest";
import {
  normalizeEmail,
  isValidEmail,
  subscribeToMailerLite,
} from "../../worker/newsletter/index.js";

describe("E-Mail-Validierung", () => {
  it("normalisiert E-Mails (trim + lowercase)", () => {
    expect(normalizeEmail("  Test@Example.COM ")).toBe("test@example.com");
  });

  it("akzeptiert gültige E-Mails", () => {
    expect(isValidEmail("a@b.co")).toBe(true);
    expect(isValidEmail("first.last+tag@sub.example.com")).toBe(true);
  });

  it("lehnt ungültige E-Mails ab", () => {
    expect(isValidEmail("nope")).toBe(false);
    expect(isValidEmail("a@b")).toBe(false);
    expect(isValidEmail("a b@c.de")).toBe(false);
  });
});

describe("subscribeToMailerLite", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("sendet status 'unconfirmed' (Regression: 'pending' war ungültig)", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response("{}", { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await subscribeToMailerLite(
      { MAILERLITE_API_KEY: "key", MAILERLITE_GROUP_ID: "group" },
      "a@b.co",
      "test",
    );

    expect(result.ok).toBe(true);
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.status).toBe("unconfirmed");
    expect(body.groups).toEqual(["group"]);
  });

  it("wertet HTTP 422 als Fehler, nicht als Erfolg", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("{}", { status: 422 })),
    );

    const result = await subscribeToMailerLite(
      { MAILERLITE_API_KEY: "key" },
      "a@b.co",
      "test",
    );

    expect(result.ok).toBe(false);
    expect(result.status).toBe(422);
  });

  it("meldet 'nicht konfiguriert' ohne API-Key", async () => {
    const result = await subscribeToMailerLite({}, "a@b.co", "test");
    expect(result.configured).toBe(false);
    expect(result.ok).toBe(false);
  });
});
