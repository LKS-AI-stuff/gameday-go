import { ApiError, useMe } from "@gamedaygo/api-client";
import { Text } from "react-native";
import { ActivityIndicator, Button, Card } from "react-native-paper";

import { useAuth } from "../auth/AuthProvider";
import { NotAffiliatedNote, Wordmark } from "../components/Brand";
import { Screen } from "../components/Screen";
import { spacing, type } from "../theme/tokens";
import { useColors } from "../theme/useTokens";

/**
 * Signed-in landing screen for M0: confirms the session reaches the backend.
 * The real Home (next games, live now, recent finals) replaces it in M1 (UI/UX §7.3).
 */
export function HomeScreen() {
  const c = useColors();
  const { userId, email, signOut } = useAuth();
  const me = useMe(userId);

  return (
    <Screen>
      <Wordmark />
      <Card mode="contained" style={{ backgroundColor: c.surface }}>
        <Card.Content style={{ gap: spacing.sm }}>
          <Text style={[type.h3, { color: c.text }]}>{"You're signed in"}</Text>
          <Text style={[type.body, { color: c.textMuted }]}>{email}</Text>
          {me.isPending ? (
            <ActivityIndicator accessibilityLabel="Loading your account" />
          ) : me.isError ? (
            <Text style={[type.body, { color: c.danger }]}>
              {me.error instanceof ApiError
                ? `Couldn't load your account (${me.error.code}).`
                : "Can't reach GameDay Go. Check your connection and try again."}
            </Text>
          ) : (
            <Text style={[type.body, { color: c.success }]}>
              Account ready{me.data.age_confirmed ? "" : " · age confirmation needed"}
            </Text>
          )}
        </Card.Content>
      </Card>
      {me.isError ? (
        <Button mode="outlined" onPress={() => me.refetch()}>
          Try again
        </Button>
      ) : null}
      <Button mode="contained" onPress={signOut}>
        Sign out
      </Button>
      <NotAffiliatedNote />
    </Screen>
  );
}
