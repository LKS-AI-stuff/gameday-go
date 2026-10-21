import { configureFonts, MD3DarkTheme, MD3LightTheme, type MD3Theme } from "react-native-paper";

import { colors, fontFamily, roundness, type ColorScheme } from "./tokens";

const base = configureFonts({ config: { fontFamily: fontFamily.body } });

const fonts = {
  ...base,
  // Paper's label variants style buttons and chips: Oswald, like the template's buttons.
  labelLarge: { ...base.labelLarge, fontFamily: fontFamily.headingMedium, letterSpacing: 0.5 },
  labelMedium: { ...base.labelMedium, fontFamily: fontFamily.headingMedium, letterSpacing: 0.5 },
  titleLarge: { ...base.titleLarge, fontFamily: fontFamily.heading },
  headlineSmall: { ...base.headlineSmall, fontFamily: fontFamily.heading },
};

export function paperTheme(scheme: ColorScheme): MD3Theme {
  const md3 = scheme === "dark" ? MD3DarkTheme : MD3LightTheme;
  const c = colors[scheme];
  return {
    ...md3,
    roundness,
    fonts,
    colors: {
      ...md3.colors,
      primary: c.primary,
      onPrimary: c.onPrimary,
      primaryContainer: c.primary,
      onPrimaryContainer: c.onPrimary,
      secondary: c.info,
      background: c.background,
      onBackground: c.text,
      surface: c.surface,
      onSurface: c.text,
      surfaceVariant: c.surfaceRaised,
      onSurfaceVariant: c.textMuted,
      outline: c.outline,
      error: c.danger,
      backdrop: c.overlay,
    },
  };
}
