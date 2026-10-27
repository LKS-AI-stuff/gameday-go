import { configureFonts, MD3DarkTheme, type MD3Theme } from "react-native-paper";

import { colors, fontFamily, roundness } from "./tokens";

const base = configureFonts({ config: { fontFamily: fontFamily.body } });

const fonts = {
  ...base,
  // Paper's label variants style buttons and chips: Oswald, like the template's buttons.
  labelLarge: { ...base.labelLarge, fontFamily: fontFamily.headingMedium, letterSpacing: 0.8 },
  labelMedium: { ...base.labelMedium, fontFamily: fontFamily.headingMedium, letterSpacing: 0.5 },
  titleLarge: { ...base.titleLarge, fontFamily: fontFamily.heading },
  headlineSmall: { ...base.headlineSmall, fontFamily: fontFamily.heading },
};

/** The single dark theme (NFR-5), used on every platform whatever the OS setting. */
export const paperTheme: MD3Theme = {
  ...MD3DarkTheme,
  dark: true,
  roundness,
  fonts,
  colors: {
    ...MD3DarkTheme.colors,
    primary: colors.primary,
    onPrimary: colors.onPrimary,
    primaryContainer: colors.primary,
    onPrimaryContainer: colors.onPrimary,
    secondary: colors.info,
    background: colors.background,
    onBackground: colors.text,
    surface: colors.surface,
    onSurface: colors.text,
    surfaceVariant: colors.surfaceRaised,
    onSurfaceVariant: colors.textMuted,
    // Text-field borders must reach 3:1; decorative borders use colors.outline directly.
    outline: colors.outlineStrong,
    outlineVariant: colors.outline,
    error: colors.danger,
    inverseSurface: colors.text,
    inverseOnSurface: colors.background,
    inversePrimary: colors.primary,
    backdrop: colors.overlay,
    elevation: {
      ...MD3DarkTheme.colors.elevation,
      level1: colors.surface,
      level2: colors.surface,
      level3: colors.surfaceRaised,
    },
  },
};
