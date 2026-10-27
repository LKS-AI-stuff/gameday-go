import type { ReactNode } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { layout, spacing } from "../theme/tokens";
import { AppBackground } from "./AppBackground";
import { Hero } from "./Hero";

interface ScreenProps {
  children: ReactNode;
  /** Narrow centered column for forms (auth screens). */
  variant?: "form" | "reading";
  /** Optional hero at the top, in the photo's dark upper area and under the status bar. */
  hero?: ReactNode;
}

/**
 * Every screen: the fixed stadium background, then safe-area, keyboard-aware scrolling content
 * with a max width. Body content goes on `Panel`s so it stays readable over the photo.
 */
export function Screen({ children, variant = "reading", hero }: ScreenProps) {
  const maxWidth = variant === "form" ? layout.formWidth : layout.readingWidth;
  return (
    <AppBackground>
      <SafeAreaView style={styles.fill} edges={hero ? ["left", "right"] : ["top", "left", "right"]}>
        <KeyboardAvoidingView
          style={styles.fill}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
        >
          <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
            {hero ? (
              <Hero underStatusBar variant={variant} overPhoto>
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
