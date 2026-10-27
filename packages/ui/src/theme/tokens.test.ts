// WCAG 2.1 AA contrast for the dark theme's tokens (NFR-3, TDD §4.4).
import { colors, type ColorTokens } from "./tokens";

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
const SURFACES: Key[] = ["hero", "background", "surface", "surfaceRaised", "chrome"];
// Tokens used for small text on any surface must reach 4.5:1.
const TEXT_ON_SURFACES: Key[] = [
  "text",
  "textMuted",
  "textSubtle",
  "primaryText",
  "info",
  "success",
  "danger",
];
const pairs = (fg: Key[], bg: Key[]) => fg.flatMap((f) => bg.map((b) => [f, b] as const));

it.each(pairs(TEXT_ON_SURFACES, SURFACES))("%s on %s meets 4.5:1", (text, surface) => {
  expect(contrast(colors[text], colors[surface])).toBeGreaterThanOrEqual(4.5);
});

it.each(SURFACES.map((s) => [s] as const))("form-field border on %s meets 3:1", (surface) => {
  expect(contrast(colors.outlineStrong, colors[surface])).toBeGreaterThanOrEqual(3);
});

it("primary-colored text buttons on the background and cards meet 4.5:1", () => {
  expect(contrast(colors.primary, colors.background)).toBeGreaterThanOrEqual(4.5);
  expect(contrast(colors.primary, colors.surface)).toBeGreaterThanOrEqual(4.5);
});

it("text on filled primary and live badges meets 4.5:1", () => {
  expect(contrast(colors.onPrimary, colors.primary)).toBeGreaterThanOrEqual(4.5);
  expect(contrast(colors.onLive, colors.live)).toBeGreaterThanOrEqual(4.5);
});

// Glass panels sit over the photo: check text against the panel blended over pure white,
// the brightest thing that could be behind it.
function blendOverWhite(rgba: string): string {
  const [r, g, b, a] = rgba.match(/[\d.]+/g)!.map(Number) as [number, number, number, number];
  const mix = (c: number) => Math.round(c * a + 255 * (1 - a));
  return "#" + [r, g, b].map((c) => mix(c).toString(16).padStart(2, "0")).join("");
}

it.each(TEXT_ON_SURFACES.map((t) => [t] as const))(
  "%s on a glass panel over the brightest photo pixel meets 4.5:1",
  (text) => {
    expect(contrast(colors[text], blendOverWhite(colors.panelGlass))).toBeGreaterThanOrEqual(4.5);
  },
);
