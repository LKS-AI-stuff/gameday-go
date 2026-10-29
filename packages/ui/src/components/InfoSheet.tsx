import type { ReactNode } from "react";
import { StyleSheet, Text } from "react-native";
import { Button, Modal, Portal } from "react-native-paper";

import { colors, spacing, type } from "../theme/tokens";

interface InfoSheetProps {
  visible: boolean;
  title: string;
  onDismiss: () => void;
  children: ReactNode;
}

/** Small sheet for one-sentence explanations (tags, exact timestamps). */
export function InfoSheet({ visible, title, onDismiss, children }: InfoSheetProps) {
  return (
    <Portal>
      <Modal visible={visible} onDismiss={onDismiss} contentContainerStyle={styles.sheet}>
        <Text style={[type.label, { color: colors.text }]} accessibilityRole="header">
          {title}
        </Text>
        {children}
        <Button onPress={onDismiss} style={styles.close}>
          Close
        </Button>
      </Modal>
    </Portal>
  );
}

const styles = StyleSheet.create({
  sheet: {
    backgroundColor: colors.surfaceRaised,
    margin: spacing.lg,
    padding: spacing.xl,
    gap: spacing.md,
    alignSelf: "center",
    maxWidth: 480,
    width: "90%",
  },
  close: { alignSelf: "flex-end" },
});
