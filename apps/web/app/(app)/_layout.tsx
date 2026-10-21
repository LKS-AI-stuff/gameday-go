import { Stack } from "expo-router";

// Bottom tabs (Home, Schedule, Plan, My Game Days) arrive with their screens in M1.
export default function AppLayout() {
  return <Stack screenOptions={{ headerShown: false }} />;
}
