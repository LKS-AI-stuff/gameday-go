// Design tokens (TDD §4.4). Every color, size and duration in the UI comes from here.

export type ColorScheme = "light" | "dark";

export interface ColorTokens {
  primary: string;
  onPrimary: string;
  primaryText: string;
  background: string;
  surface: string;
  surfaceRaised: string;
  outline: string;
  text: string;
  textMuted: string;
  info: string;
  live: string;
  onLive: string;
  success: string;
  danger: string;
  overlay: string;
}

export const colors: Record<ColorScheme, ColorTokens> = {
  light: {
    primary: "#F0502A",
    onPrimary: "#111111",
    primaryText: "#C23A16",
    background: "#F5F5F5",
    surface: "#FFFFFF",
    surfaceRaised: "#FFFFFF",
    outline: "#D9D9D9",
    text: "#111111",
    textMuted: "#5C5C5C",
    info: "#1051ED",
    live: "#F1C50E",
    onLive: "#111111",
    success: "#137A74",
    danger: "#C62828",
    overlay: "rgba(0,0,0,0.5)",
  },
  dark: {
    primary: "#F0502A",
    onPrimary: "#111111",
    primaryText: "#FF7A57",
    background: "#111111",
    surface: "#1A1A1A",
    surfaceRaised: "#262626",
    outline: "#333333",
    text: "#FFFFFF",
    textMuted: "#B9C1CC",
    info: "#6690F4",
    live: "#F1C50E",
    onLive: "#111111",
    success: "#2CCCC4",
    danger: "#F26360",
    overlay: "rgba(0,0,0,0.5)",
  },
};

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
  minTouchTarget: 48,
} as const;

export const motion = {
  enterMs: 300,
  enterRisePx: 12,
  staggerMs: 50,
  scorePulseMs: 600,
  traceStepMs: 200,
} as const;
