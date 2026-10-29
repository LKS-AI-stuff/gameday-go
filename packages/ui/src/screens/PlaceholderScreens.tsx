import { StyleSheet, View } from "react-native";
import { IconButton } from "react-native-paper";

import { AppBar, type AppBarActions } from "../components/AppBar";
import { SectionTitle } from "../components/Panel";
import { Screen } from "../components/Screen";
import { EmptyState } from "../components/StateViews";
import { colors } from "../theme/tokens";

interface ComingSoonScreenProps extends AppBarActions {
  title: string;
  icon: string;
  message: string;
}

/** Plan and My Game Days tabs until M3 and M5. */
export function ComingSoonScreen({ title, icon, message, ...appBar }: ComingSoonScreenProps) {
  return (
    <Screen>
      <AppBar {...appBar} />
      <SectionTitle>{title}</SectionTitle>
      <EmptyState icon={icon} title={message} />
    </Screen>
  );
}

/** Alert history arrives with Alerts in M5 (FR-N1). */
export function InboxScreen({ onBack }: { onBack: () => void }) {
  return (
    <Screen>
      <View style={styles.header}>
        <IconButton
          icon="arrow-left"
          iconColor={colors.text}
          onPress={onBack}
          accessibilityLabel="Back"
        />
        <SectionTitle>INBOX</SectionTitle>
      </View>
      <EmptyState
        icon="bell-outline"
        title="No alerts yet"
        body="Alerts you set up and schedule changes for your games will show here."
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "center" },
});
