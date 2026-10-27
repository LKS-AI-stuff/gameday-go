import { ApiError, useMe } from "@gamedaygo/api-client";
import { StyleSheet, Text, View } from "react-native";
import { ActivityIndicator, Button } from "react-native-paper";

import { useAuth } from "../auth/AuthProvider";
import { NotAffiliatedNote, Wordmark } from "../components/Brand";
import { Panel, SectionTitle } from "../components/Panel";
import { Screen } from "../components/Screen";
import { colors, spacing, type } from "../theme/tokens";

/**
 * Signed-in landing screen for M0: confirms the session reaches the backend.
 * The real Home (next games, live now, recent finals) replaces it in M1 (UI/UX §7.3).
 */
export function HomeScreen() {
  const { userId, email, signOut } = useAuth();
  const me = useMe(userId);

  return (
    <Screen>
      <View style={styles.appBar}>
        <Wordmark size="compact" />
      </View>
      <SectionTitle>YOUR ACCOUNT</SectionTitle>
      <Panel
        variant="glass"
        accent={me.isSuccess ? colors.success : undefined}
        style={styles.panel}
      >
        <Text style={[type.h3, { color: colors.text }]}>{"You're signed in"}</Text>
        <Text style={[type.body, { color: colors.textMuted }]}>{email}</Text>
        {me.isPending ? (
          <ActivityIndicator accessibilityLabel="Loading your account" />
        ) : me.isError ? (
          <Text style={[type.body, { color: colors.danger }]}>
            {me.error instanceof ApiError
              ? `Couldn't load your account (${me.error.code}).`
              : "Can't reach GameDay Go. Check your connection and try again."}
          </Text>
        ) : (
          <Text style={[type.body, { color: colors.success }]}>
            Account ready{me.data.age_confirmed ? "" : " · age confirmation needed"}
          </Text>
        )}
        {me.isError ? (
          <Button mode="outlined" onPress={() => me.refetch()}>
            Try again
          </Button>
        ) : null}
        <Button mode="contained" onPress={signOut} style={styles.signOut}>
          Sign out
        </Button>
        <NotAffiliatedNote />
      </Panel>
    </Screen>
  );
}

const styles = StyleSheet.create({
  appBar: { paddingVertical: spacing.sm },
  panel: { padding: spacing.xl, gap: spacing.md },
  signOut: { marginTop: spacing.sm },
});
