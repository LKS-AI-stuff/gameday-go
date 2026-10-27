import type { ReactNode } from "react";
import { StyleSheet, Text, View, type ViewStyle } from "react-native";

import { colors, spacing, type } from "../theme/tokens";

interface PanelProps {
  children: ReactNode;
  /** A 3 px top border in an accent color (e.g. `colors.live` for live games). */
  accent?: string;
  /** `glass` over the background photo (mostly opaque, so text contrast never depends on it). */
  variant?: "solid" | "glass";
  style?: ViewStyle;
}

/** Card in the mockup's style: dark surface, thin border, square corners. */
export function Panel({ children, accent, variant = "solid", style }: PanelProps) {
  return (
    <View
      style={[
        styles.panel,
        variant === "glass" ? styles.glass : null,
        accent ? { borderTopWidth: 3, borderTopColor: accent } : null,
        style,
      ]}
    >
      {children}
    </View>
  );
}

/** Uppercase Oswald section title ("YOUR NEXT GAMES"). */
export function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <Text style={[type.h2, styles.title]} accessibilityRole="header">
      {children}
    </Text>
  );
}

const styles = StyleSheet.create({
  panel: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.outline,
    padding: spacing.lg,
    gap: spacing.sm,
  },
  glass: { backgroundColor: colors.panelGlass },
  title: { color: colors.text, fontSize: 18, lineHeight: 24, letterSpacing: 0.5 },
});
