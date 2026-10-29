/**
 * Generates the OpenGraph preview image (public/og-default.png)
 * from the source SVG (public/og-default.svg).
 *
 * Uses sharp (libvips) for a deterministic, dependency-light
 * SVG -> PNG conversion. Runs automatically before `npm run build`
 * via the `prebuild` script, and can be triggered manually with
 * `npm run og:generate`.
 */
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { stat } from "node:fs/promises";
import sharp from "sharp";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const input = join(root, "public", "og-default.svg");
const output = join(root, "public", "og-default.png");

const WIDTH = 1200;
const HEIGHT = 630;

try {
  await stat(input);
} catch {
  console.error(`[og] Source SVG not found: ${input}`);
  process.exit(1);
}

// Render at 2x density for crisp text, then downscale to the
// canonical 1200x630 OpenGraph size.
await sharp(input, { density: 144 })
  .resize(WIDTH, HEIGHT, { fit: "cover" })
  .png({ compressionLevel: 9, adaptiveFiltering: true })
  .toFile(output);

const { size } = await stat(output);
const meta = await sharp(output).metadata();

console.log(
  `[og] Generated ${output} (${meta.width}x${meta.height}, ${meta.format}, ${(size / 1024).toFixed(1)} KB)`
);
