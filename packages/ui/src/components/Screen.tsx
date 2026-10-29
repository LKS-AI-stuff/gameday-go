import type { ReactElement, ReactNode } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  View,
  type RefreshControlProps,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { layout, spacing } from "../theme/tokens";
import { AppBackground } from "./AppBackground";
import { Hero } from "./Hero";

interface ScreenProps {
  children: ReactNode;
  /** Narrow centered column for forms, the reading width, or wide for card grids. */
  variant?: "form" | "reading" | "wide";
  /** Optional hero at the top, in the photo's dark upper area and under the status bar. */
  hero?: ReactNode;
  /** Draw the hero as the black band with field lines (game detail) instead of over the photo. */
  heroBand?: boolean;
  /** Pull-to-refresh (UI/UX §5.6). */
  refreshControl?: ReactElement<RefreshControlProps>;
}

/**
 * Every screen: the fixed stadium background, then safe-area, keyboard-aware scrolling content
 * with a max width. Body content goes on `Panel`s so it stays readable over the photo.
 */
export function Screen({
  children,
  variant = "reading",
  hero,
  heroBand = false,
  refreshControl,
}: ScreenProps) {
  const maxWidth =
    variant === "form"
      ? layout.formWidth
      : variant === "wide"
        ? layout.wideWidth
        : layout.readingWidth;
  return (
    <AppBackground>
      <SafeAreaView style={styles.fill} edges={hero ? ["left", "right"] : ["top", "left", "right"]}>
        <KeyboardAvoidingView
          style={styles.fill}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
        >
          <ScrollView
            contentContainerStyle={styles.scroll}
            keyboardShouldPersistTaps="handled"
            refreshControl={refreshControl}
          >
            {hero ? (
              <Hero
                underStatusBar
                variant={variant === "form" ? "form" : "reading"}
                overPhoto={!heroBand}
              >
                {hero}
              </Hero>
            ) : null}
            <SafeAreaView edges={["bottom"]} style={styles.body}>
              <View style={[styles.column, { maxWidth }]}>{children}</View>
            </SafeAreaView>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </AppBackground>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  scroll: { flexGrow: 1 },
  body: { flexGrow: 1, padding: spacing.lg },
  column: { width: "100%", alignSelf: "center", gap: spacing.lg },
});
