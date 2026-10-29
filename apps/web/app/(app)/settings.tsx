import { SettingsScreen } from "@gamedaygo/ui";
import Constants from "expo-constants";
import { useRouter } from "expo-router";

export default function SettingsRoute() {
  const router = useRouter();
  return (
    <SettingsScreen
      appVersion={Constants.expoConfig?.version ?? "dev"}
      onBack={() => (router.canGoBack() ? router.back() : router.replace("/home"))}
    />
  );
}
