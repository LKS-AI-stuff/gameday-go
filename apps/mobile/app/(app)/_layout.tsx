import { useMe } from "@gamedaygo/api-client";
import { ErrorState, Screen, useAuth } from "@gamedaygo/ui";
import { Button } from "react-native-paper";
import { Stack } from "expo-router";

// Signed-in users finish onboarding before anything else (TDD §4.3, FR-P1).
export default function AppLayout() {
  const { userId, signOut } = useAuth();
  const me = useMe(userId);

  if (me.isPending) return null;
  if (!me.data) {
    return (
      <Screen>
        <ErrorState error={me.error} onRetry={() => void me.refetch()} />
        <Button mode="text" onPress={() => void signOut()}>
          Sign out
        </Button>
      </Screen>
    );
  }
  const onboarded = me.data.onboarded;
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Protected guard={onboarded}>
        <Stack.Screen name="(tabs)" />
      </Stack.Protected>
      <Stack.Protected guard={!onboarded}>
        <Stack.Screen name="onboarding" />
      </Stack.Protected>
    </Stack>
  );
}
