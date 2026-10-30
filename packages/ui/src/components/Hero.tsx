import type { ReactNode } from "react";
import { StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { layout, spacing } from "../theme/tokens";

interface HeroProps {
  children: ReactNode;
  /** Extend under the status bar (the hero is the top of the screen). */
  underStatusBar?: boolean;
  /** Matches the screen's column: auth forms, onboarding, or the signed-in pages' width. */
  variant?: "form" | "reading" | "wide";
}

/** The screen's header, drawn straight over the dark upper part of the background photo
 * (UI/UX §4, §6.2). */
export function Hero({ children, underStatusBar = false, variant = "wide" }: HeroProps) {
  const insets = useSafeAreaInsets();
  const maxWidth =
    variant === "form"
      ? layout.formWidth
      : variant === "wide"
        ? layout.wideWidth
        : layout.readingWidth;
  return (
    <View style={[styles.hero, { paddingTop: (underStatusBar ? insets.top : 0) + spacing.xxl }]}>
      <View style={[styles.content, { maxWidth }]}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  hero: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xl,
  },
  content: { width: "100%", alignSelf: "center", gap: spacing.sm },
});
