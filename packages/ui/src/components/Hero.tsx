import type { ReactNode } from "react";
import { StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors, layout, spacing } from "../theme/tokens";
import { FieldLines } from "./FieldLines";

interface HeroProps {
  children: ReactNode;
  /** Extend under the status bar (the hero is the top of the screen). */
  underStatusBar?: boolean;
  /** Narrow content column (auth screens) or the reading width. */
  variant?: "form" | "reading";
  /** Over the background photo: no black band or drawn field lines, the photo shows through. */
  overPhoto?: boolean;
}

/** Full-bleed black band with the field-line pattern: the template's hero (UI/UX §4, §6.2). */
export function Hero({
  children,
  underStatusBar = false,
  variant = "reading",
  overPhoto = false,
}: HeroProps) {
  const insets = useSafeAreaInsets();
  const maxWidth = variant === "form" ? layout.formWidth : layout.readingWidth;
  return (
    <View
      style={[
        styles.hero,
        overPhoto ? styles.overPhoto : null,
        { paddingTop: (underStatusBar ? insets.top : 0) + spacing.xxl },
      ]}
    >
      {overPhoto ? null : <FieldLines />}
      <View style={[styles.content, { maxWidth }]}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  hero: {
    backgroundColor: colors.hero,
    overflow: "hidden",
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xl,
  },
  overPhoto: { backgroundColor: "transparent" },
  content: { width: "100%", alignSelf: "center", gap: spacing.sm },
});
