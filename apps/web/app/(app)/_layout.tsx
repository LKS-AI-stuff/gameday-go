import { useMe } from "@gamedaygo/api-client";
import { AppBackground, ErrorState, Screen, SideNav, TABS, useAuth } from "@gamedaygo/ui";
import { DarkTheme, Stack, ThemeProvider, router, usePathname, type Href } from "expo-router";
import { StyleSheet, useWindowDimensions, View } from "react-native";
import { Button } from "react-native-paper";

// Signed-in users finish onboarding before anything else (TDD §4.3, FR-P1). On wide windows,
// every page after onboarding sits beside the side navigation, with one background photo
// behind both (UI/UX §2.2).
export default function AppLayout() {
  const { userId, signOut } = useAuth();
  const me = useMe(userId);
  const { width } = useWindowDimensions();
  const pathname = usePathname();

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
  const wide = width >= 1024;
  const stack = (
    <Stack
      screenOptions={{
        headerShown: false,
        // Wide: let the photo behind the side navigation and the page show through.
        contentStyle: wide ? { backgroundColor: "transparent" } : undefined,
      }}
    >
      <Stack.Protected guard={onboarded}>
        <Stack.Screen name="(tabs)" />
      </Stack.Protected>
      <Stack.Protected guard={!onboarded}>
        <Stack.Screen name="onboarding" />
      </Stack.Protected>
    </Stack>
  );
  if (!onboarded || !wide) return stack;

  const current = TABS.find((tab) => pathname === `/${tab.name}`)?.name ?? null;
  return (
    <AppBackground>
      <ThemeProvider value={SEE_THROUGH}>
        <View style={styles.row}>
          <SideNav
            items={TABS}
            current={current}
            onNavigate={(name) => router.navigate(`/${name}` as Href)}
          />
          <View style={styles.page}>{stack}</View>
        </View>
      </ThemeProvider>
    </AppBackground>
  );
}

// Navigators paint their theme's background behind every page; on wide web it must be
// transparent so the photo behind the side navigation and the page shows through.
const SEE_THROUGH = { ...DarkTheme, colors: { ...DarkTheme.colors, background: "transparent" } };

const styles = StyleSheet.create({
  row: { flex: 1, flexDirection: "row" },
  page: { flex: 1 },
});
