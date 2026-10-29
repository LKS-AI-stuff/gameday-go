import { useMe } from "@gamedaygo/api-client";
import { ErrorState, Screen, useAuth } from "@gamedaygo/ui";
import { Stack } from "expo-router";

// Signed-in users finish onboarding before anything else (TDD §4.3, FR-P1).
export default function AppLayout() {
  const { userId } = useAuth();
  const me = useMe(userId);

  if (me.isPending) return null;
  if (!me.data) {
    return (
      <Screen>
        <ErrorState error={me.error} onRetry={() => void me.refetch()} />
      </Screen>
    );
  }
  const onboarded = me.data.onboarded;
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Protected guard={onboarded}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="games/[id]" />
        <Stack.Screen name="settings" />
        <Stack.Screen name="inbox" />
      </Stack.Protected>
      <Stack.Protected guard={!onboarded}>
        <Stack.Screen name="onboarding" />
      </Stack.Protected>
    </Stack>
  );
}
