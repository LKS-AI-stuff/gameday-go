import type { ReactNode } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { layout, spacing } from "../theme/tokens";
import { useColors } from "../theme/useTokens";

interface ScreenProps {
  children: ReactNode;
  /** Narrow centered column for forms (auth screens). */
  variant?: "form" | "reading";
}

/** Safe-area, keyboard-aware, scrollable screen with a max content width on wide screens. */
export function Screen({ children, variant = "reading" }: ScreenProps) {
  const c = useColors();
  const maxWidth = variant === "form" ? layout.formWidth : layout.readingWidth;
  return (
    <SafeAreaView style={[styles.fill, { backgroundColor: c.background }]}>
      <KeyboardAvoidingView
        style={styles.fill}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <View style={[styles.column, { maxWidth }]}>{children}</View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  scroll: { flexGrow: 1, justifyContent: "center", padding: spacing.lg },
  column: { width: "100%", alignSelf: "center", gap: spacing.lg },
});
