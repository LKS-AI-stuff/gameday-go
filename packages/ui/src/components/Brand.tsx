import { APP_NAME, NOT_AFFILIATED, TAGLINE } from "@gamedaygo/shared";
import { Platform, StyleSheet, Text, View } from "react-native";

import { displayWeb, spacing, type } from "../theme/tokens";
import { useColors } from "../theme/useTokens";

/** Text wordmark "GAMEDAY GO" with the tagline (UX1). */
export function Wordmark({ tagline = true }: { tagline?: boolean }) {
  const c = useColors();
  return (
    <View style={styles.wordmark} accessibilityRole="header">
      <Text style={[Platform.OS === "web" ? displayWeb : type.display, { color: c.text }]}>
        {APP_NAME}
      </Text>
      {tagline ? <Text style={[type.body, { color: c.textMuted }]}>{TAGLINE}</Text> : null}
    </View>
  );
}

/** "Not affiliated with the NFL" note (NFR-17). */
export function NotAffiliatedNote() {
  const c = useColors();
  return (
    <Text style={[type.caption, styles.center, { color: c.textMuted }]}>{NOT_AFFILIATED}</Text>
  );
}

const styles = StyleSheet.create({
  wordmark: { gap: spacing.xs, marginBottom: spacing.sm },
  center: { textAlign: "center" },
});
