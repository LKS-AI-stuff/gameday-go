import { GameDetailScreen } from "@gamedaygo/ui";
import { useLocalSearchParams, useRouter } from "expo-router";

export default function GameRoute() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  return (
    <GameDetailScreen
      gameId={id}
      onBack={() => (router.canGoBack() ? router.back() : router.replace("/schedule"))}
    />
  );
}
