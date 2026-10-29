import { useGames, usePreferences, useSeason, type GameSummary } from "@gamedaygo/api-client";
import { COPY } from "@gamedaygo/shared";
import { useMemo, useState } from "react";
import { RefreshControl } from "react-native";

import { AppBar, type AppBarActions } from "../components/AppBar";
import { CardGrid } from "../components/CardGrid";
import { GameCard } from "../components/GameCard";
import { SectionTitle } from "../components/Panel";
import { Screen } from "../components/Screen";
import {
  EmptyState,
  ErrorState,
  isOffline,
  OfflineBanner,
  Skeleton,
} from "../components/StateViews";
import { useViewer } from "../hooks/useViewer";
import { colors } from "../theme/tokens";

const MAX_NEXT_GAMES = 5;

/** The next game for each favorite team, by kickoff, at most five (UI/UX §7.3, FR-SC1). */
export function nextGamesPerTeam(
  games: GameSummary[],
  favorites: string[],
  now: Date = new Date(),
): GameSummary[] {
  const covered = new Set<string>();
  const picked: GameSummary[] = [];
  for (const game of games) {
    // Tabs stay mounted, so the list can be older than the games in it.
    if (game.kickoff_at && !game.kickoff_tbd && new Date(game.kickoff_at) <= now) continue;
    const teams = [game.home?.id, game.away?.id].filter(
      (id): id is string => !!id && favorites.includes(id) && !covered.has(id),
    );
    if (teams.length === 0) continue;
    teams.forEach((id) => covered.add(id));
    picked.push(game);
    if (picked.length === MAX_NEXT_GAMES) break;
  }
  return picked;
}

interface HomeScreenProps extends AppBarActions {
  onOpenGame: (id: string) => void;
  onBrowseSchedule: () => void;
}

/** UI/UX §7.3. "Live now" and "Recent finals" arrive with scores in M4. */
export function HomeScreen({ onOpenGame, onBrowseSchedule, ...appBar }: HomeScreenProps) {
  const { userId, timeZone } = useViewer();
  const season = useSeason(userId);
  const preferences = usePreferences(userId);
  // Fixed per mount so the query key is stable; pull-to-refresh moves it forward.
  const [from, setFrom] = useState(() => new Date().toISOString());
  const games = useGames(
    userId,
    { favorites: true, from, limit: 40 },
    season.data?.schedule_available === true,
  );
  const [refreshing, setRefreshing] = useState(false);

  const next = useMemo(
    () => nextGamesPerTeam(games.data?.items ?? [], preferences.data?.favorite_team_ids ?? []),
    [games.data, preferences.data],
  );

  const refresh = async () => {
    setRefreshing(true);
    setFrom(new Date().toISOString());
    await Promise.all([season.refetch(), preferences.refetch(), games.refetch()]);
    setRefreshing(false);
  };

  let body;
  if (season.isPending || (season.data?.schedule_available && games.isPending)) {
    body = <Skeleton rows={3} />;
  } else if (season.isError && !season.data) {
    body = <ErrorState error={season.error} onRetry={() => void season.refetch()} />;
  } else if (season.data && !season.data.schedule_available) {
    body = (
      <EmptyState
        icon="calendar-blank"
        title={COPY.scheduleNotOut}
        body={COPY.scheduleNotOutDetail}
      />
    );
  } else if (games.isError && !games.data) {
    body = <ErrorState error={games.error} onRetry={() => void games.refetch()} />;
  } else if (next.length === 0) {
    body = (
      <EmptyState
        icon="calendar-check"
        title={COPY.noMoreGames}
        action={{ label: "Browse schedule", onPress: onBrowseSchedule }}
      />
    );
  } else {
    body = (
      <CardGrid>
        {next.map((game) => (
          <GameCard
            key={game.id}
            game={game}
            timeZone={timeZone}
            onPress={() => onOpenGame(game.id)}
          />
        ))}
      </CardGrid>
    );
  }

  return (
    <Screen
      variant="wide"
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => void refresh()}
          tintColor={colors.text}
        />
      }
    >
      <AppBar {...appBar} />
      <OfflineBanner visible={isOffline(games) || isOffline(season)} />
      <SectionTitle>YOUR NEXT GAMES</SectionTitle>
      {body}
    </Screen>
  );
}
