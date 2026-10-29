// Design tokens (TDD §4.4). Every color, size and duration in the UI comes from here.

// One dark theme on every platform, whatever the device's light/dark setting (NFR-5).
// Values follow the approved mockup and the reference template's dark sections.
export interface ColorTokens {
  primary: string;
  onPrimary: string;
  primaryText: string;
  /** Hero bands and the auth screens' header (template: black under a field-line pattern). */
  hero: string;
  background: string;
  surface: string;
  surfaceRaised: string;
  /** Bottom navigation and app chrome. */
  chrome: string;
  /** Decorative borders and dividers only (cards, rows). */
  outline: string;
  /** Form-field borders: at least 3:1 against every surface (WCAG 1.4.11). */
  outlineStrong: string;
  /** Lines of the field pattern, drawn at `fieldLineOpacity`. */
  fieldLine: string;
  text: string;
  textMuted: string;
  /** De-emphasized captions: sources, timestamps, "@" in matchups. */
  textSubtle: string;
  info: string;
  live: string;
  onLive: string;
  success: string;
  danger: string;
  overlay: string;
  /** Over the background photo, so it stays vivid but recedes. */
  scrim: string;
  /** Panels over the background photo: text on them never depends on what's behind. */
  panelGlass: string;
}

export const colors: ColorTokens = {
  primary: "#F0502A",
  onPrimary: "#111111",
  primaryText: "#FF7A57",
  hero: "#000000",
  background: "#111111",
  surface: "#1A1A1A",
  surfaceRaised: "#262626",
  chrome: "#0B0B0B",
  outline: "#333333",
  outlineStrong: "#767676",
  fieldLine: "#FFFFFF",
  text: "#FFFFFF",
  textMuted: "#B9C1CC",
  textSubtle: "#8E96A3",
  info: "#6690F4",
  live: "#F1C50E",
  onLive: "#111111",
  success: "#2CCCC4",
  danger: "#F26360",
  overlay: "rgba(0,0,0,0.6)",
  scrim: "rgba(0,0,0,0.35)",
  panelGlass: "rgba(17,17,17,0.9)",
};

/** The field-line pattern (UI/UX §4): yard lines every 40 px, at 16% opacity. */
export const fieldPattern = {
  lineOpacity: 0.16,
  yardSpacing: 40,
} as const;

export const fontFamily = {
  display: "Oswald_700Bold",
  heading: "Oswald_600SemiBold",
  headingMedium: "Oswald_500Medium",
  body: "OpenSans_400Regular",
  bodySemiBold: "OpenSans_600SemiBold",
} as const;

export interface TypeToken {
  fontFamily: string;
  fontSize: number;
  lineHeight: number;
  textTransform?: "uppercase";
  letterSpacing?: number;
}

export const type = {
  display: {
    fontFamily: fontFamily.display,
    fontSize: 36,
    lineHeight: 42,
    textTransform: "uppercase",
  },
  h1: { fontFamily: fontFamily.heading, fontSize: 28, lineHeight: 34, textTransform: "uppercase" },
  h2: {
    fontFamily: fontFamily.headingMedium,
    fontSize: 22,
    lineHeight: 28,
    textTransform: "uppercase",
  },
  h3: { fontFamily: fontFamily.headingMedium, fontSize: 18, lineHeight: 24 },
  body: { fontFamily: fontFamily.body, fontSize: 16, lineHeight: 24 },
  label: {
    fontFamily: fontFamily.headingMedium,
    fontSize: 14,
    lineHeight: 20,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  caption: { fontFamily: fontFamily.body, fontSize: 13, lineHeight: 18 },
  score: { fontFamily: fontFamily.display, fontSize: 32, lineHeight: 36 },
} satisfies Record<string, TypeToken>;

// Web uses a larger display size (TDD §4.4).
export const displayWeb: TypeToken = { ...type.display, fontSize: 48, lineHeight: 56 };

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32, xxxl: 48 } as const;

// Near-square corners, like the reference template (Paper roundness 2).
export const roundness = 2;

export const layout = {
  /** Max width for forms, chat and reading text on wide screens (UI/UX §3). */
  readingWidth: 720,
  /** Auth forms are narrower still. */
  formWidth: 440,
  /** Card grids on desktop web (UI/UX §3: content max 1200 px). */
  wideWidth: 1200,
  minTouchTarget: 48,
} as const;

export const motion = {
  enterMs: 300,
  enterRisePx: 12,
  staggerMs: 50,
  scorePulseMs: 600,
  traceStepMs: 200,
} as const;
