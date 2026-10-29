import { StyleSheet, View } from "react-native";
import { IconButton } from "react-native-paper";

import { colors, spacing } from "../theme/tokens";
import { Wordmark } from "./Brand";

export interface AppBarActions {
  onOpenInbox: () => void;
  onOpenSettings: () => void;
}

/** Wordmark with the inbox bell and settings gear (UI/UX §2.2). */
export function AppBar({ onOpenInbox, onOpenSettings }: AppBarActions) {
  return (
    <View style={styles.bar}>
      <Wordmark size="compact" />
      <View style={styles.actions}>
        <IconButton
          icon="bell-outline"
          iconColor={colors.text}
          onPress={onOpenInbox}
          accessibilityLabel="Inbox"
        />
        <IconButton
          icon="cog-outline"
          iconColor={colors.text}
          onPress={onOpenSettings}
          accessibilityLabel="Settings"
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: spacing.xs,
  },
  actions: { flexDirection: "row", marginRight: -spacing.sm },
});
