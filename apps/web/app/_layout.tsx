import { AppProviders, useAppFonts, useAuth } from "@gamedaygo/ui";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

import { env } from "../src/env";
import { supabase } from "../src/supabase";

function RootNavigator() {
  const { status } = useAuth();
  const fontsReady = useAppFonts();

  if (!fontsReady || status === "loading") return null;
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index" />
      <Stack.Protected guard={status === "signedIn"}>
        <Stack.Screen name="(app)" />
      </Stack.Protected>
      <Stack.Protected guard={status === "signedOut"}>
        <Stack.Screen name="(auth)" />
      </Stack.Protected>
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <AppProviders
      supabase={supabase}
      apiUrl={env.apiUrl}
      // The verification link returns to this web app, which then signs the user in.
      emailRedirectTo={globalThis.location?.origin}
    >
      <StatusBar style="light" />
      <RootNavigator />
    </AppProviders>
  );
}
