import { APP_NAME, NOT_AFFILIATED, TAGLINE } from "@gamedaygo/shared";
import { Platform, StyleSheet, Text, View } from "react-native";

import { colors, displayWeb, spacing, type } from "../theme/tokens";

interface WordmarkProps {
  /** `display` for heroes, `compact` for the app bar. */
  size?: "display" | "compact";
  tagline?: boolean;
}

/** Text wordmark "GAMEDAY GO" with an orange "GO", as in the mockup (UX1). */
export function Wordmark({ size = "display", tagline = false }: WordmarkProps) {
  const base =
    size === "compact" ? styles.compact : Platform.OS === "web" ? displayWeb : type.display;
  return (
    <View style={styles.wordmark}>
      <Text
        style={[base, { color: colors.text }]}
        accessibilityRole="header"
        accessibilityLabel={APP_NAME}
      >
        GAMEDAY <Text style={{ color: colors.primary }}>GO</Text>
      </Text>
      {tagline ? <Text style={[type.body, { color: colors.textMuted }]}>{TAGLINE}</Text> : null}
    </View>
  );
}

/** A screen's title inside a hero, under the wordmark. */
export function HeroTitle({ children }: { children: string }) {
  return <Text style={[type.h1, { color: colors.text }]}>{children}</Text>;
}

/** "Not affiliated with the NFL" note (NFR-17). */
export function NotAffiliatedNote() {
  return (
    <Text style={[type.caption, styles.center, { color: colors.textSubtle }]}>
      {NOT_AFFILIATED}
    </Text>
  );
}

const styles = StyleSheet.create({
  wordmark: { gap: spacing.xs },
  compact: { ...type.h3, fontFamily: type.display.fontFamily, fontSize: 24, letterSpacing: 1 },
  center: { textAlign: "center" },
});
