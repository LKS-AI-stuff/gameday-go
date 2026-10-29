import { HomeScreen } from "@gamedaygo/ui";
import { useRouter } from "expo-router";

export default function HomeRoute() {
  const router = useRouter();
  return (
    <HomeScreen
      onOpenGame={(id) => router.push({ pathname: "/games/[id]", params: { id } })}
      onBrowseSchedule={() => router.navigate("/schedule")}
      onOpenInbox={() => router.push("/inbox")}
      onOpenSettings={() => router.push("/settings")}
    />
  );
}
