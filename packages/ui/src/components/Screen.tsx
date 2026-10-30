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

import { useTabBarSpace } from "../navigation";
import { layout, spacing } from "../theme/tokens";
import { AppBackground } from "./AppBackground";
import { Hero } from "./Hero";

interface ScreenProps {
  children: ReactNode;
  /** Signed-in pages are `wide` (the default), so every page shares one width and left edge;
   * `reading` is the narrower onboarding column and `form` the auth forms. */
  variant?: "form" | "reading" | "wide";
  /** Optional hero at the top, in the photo's dark upper area and under the status bar. */
  hero?: ReactNode;
  /** Pull-to-refresh (UI/UX §5.6). */
  refreshControl?: ReactElement<RefreshControlProps>;
}

/**
 * Every screen: the fixed stadium background, then safe-area, keyboard-aware scrolling content
 * with a max width. Body content goes on `Panel`s so it stays readable over the photo.
 */
export function Screen({ children, variant = "wide", hero, refreshControl }: ScreenProps) {
  // Keep the last content clear of a floating bottom tab bar (it covers the safe area too).
  const tabBarSpace = useTabBarSpace();
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
              <Hero underStatusBar variant={variant}>
                {hero}
              </Hero>
            ) : null}
            <SafeAreaView
              edges={tabBarSpace ? [] : ["bottom"]}
              style={[
                styles.body,
                tabBarSpace ? { paddingBottom: tabBarSpace + spacing.lg } : null,
              ]}
            >
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
