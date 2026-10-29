import { InboxScreen } from "@gamedaygo/ui";
import { useRouter } from "expo-router";

// Alert history arrives with Alerts in M5.
export default function InboxRoute() {
  const router = useRouter();
  return (
    <InboxScreen onBack={() => (router.canGoBack() ? router.back() : router.replace("/home"))} />
  );
}
