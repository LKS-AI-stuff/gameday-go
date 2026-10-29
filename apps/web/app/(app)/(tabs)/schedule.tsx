import { ScheduleScreen } from "@gamedaygo/ui";
import { useRouter } from "expo-router";

export default function ScheduleRoute() {
  const router = useRouter();
  return (
    <ScheduleScreen
      onOpenGame={(id) => router.push({ pathname: "/games/[id]", params: { id } })}
      onOpenInbox={() => router.push("/inbox")}
      onOpenSettings={() => router.push("/settings")}
    />
  );
}
