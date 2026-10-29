import { ComingSoonScreen } from "@gamedaygo/ui";
import { useRouter } from "expo-router";

// The planner arrives in M3.
export default function PlanRoute() {
  const router = useRouter();
  return (
    <ComingSoonScreen
      title="PLAN"
      icon="map-marker-path"
      message="Planning arrives soon"
      onOpenInbox={() => router.push("/inbox")}
      onOpenSettings={() => router.push("/settings")}
    />
  );
}
