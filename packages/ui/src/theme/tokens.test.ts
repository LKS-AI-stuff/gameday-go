// WCAG 2.1 AA contrast for text tokens (NFR-3, TDD §4.4).
import { colors, type ColorScheme, type ColorTokens } from "./tokens";

function luminance(hex: string): number {
  const channels = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = channels.map((c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!;
}

export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi! + 0.05) / (lo! + 0.05);
}

type Key = keyof ColorTokens;
const SURFACES: Key[] = ["background", "surface", "surfaceRaised"];
// Tokens used for small text on any surface must reach 4.5:1.
const TEXT_ON_SURFACES: Key[] = ["text", "textMuted", "primaryText", "info", "success", "danger"];

describe.each(["light", "dark"] as ColorScheme[])("%s theme", (scheme) => {
  const c = colors[scheme];

  it.each(TEXT_ON_SURFACES.flatMap((t) => SURFACES.map((s) => [t, s] as const)))(
    "%s on %s meets 4.5:1",
    (text, surface) => {
      expect(contrast(c[text], c[surface])).toBeGreaterThanOrEqual(4.5);
    },
  );

  it("onPrimary on primary meets 4.5:1", () => {
    expect(contrast(c.onPrimary, c.primary)).toBeGreaterThanOrEqual(4.5);
  });

  it("onLive on live meets 4.5:1", () => {
    expect(contrast(c.onLive, c.live)).toBeGreaterThanOrEqual(4.5);
  });
});
