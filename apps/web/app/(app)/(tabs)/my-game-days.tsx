import { ComingSoonScreen } from "@gamedaygo/ui";
import { useRouter } from "expo-router";

// Saved plans arrive in M3, Alerts in M5.
export default function MyGameDaysRoute() {
  const router = useRouter();
  return (
    <ComingSoonScreen
      title="MY GAME DAYS"
      icon="bookmark-outline"
      message="Your saved plans and alerts will show here"
      onOpenInbox={() => router.push("/inbox")}
      onOpenSettings={() => router.push("/settings")}
    />
  );
}
