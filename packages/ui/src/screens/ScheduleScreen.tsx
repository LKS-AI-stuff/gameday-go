import { useAllGames, useGames, useSeason, useTeams } from "@gamedaygo/api-client";
import { COPY, formatDayHeader, gameDayKey } from "@gamedaygo/shared";
import { useEffect, useMemo, useRef, useState, type ComponentRef } from "react";
import { RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { Button, Chip, Modal, Portal } from "react-native-paper";

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
import { TeamPicker } from "../components/TeamPicker";
import { useViewer } from "../hooks/useViewer";
import { colors, spacing, type } from "../theme/tokens";

const CHIP_STEP = 96;
const REGULAR_SEASON_WEEKS = 18;

interface ScheduleScreenProps extends AppBarActions {
  onOpenGame: (id: string) => void;
}

/** Season by week with a team filter and "My teams" (UI/UX §7.4, FR-SC2). */
export function ScheduleScreen({ onOpenGame, ...appBar }: ScheduleScreenProps) {
  const { userId, timeZone } = useViewer();
  const season = useSeason(userId);
  const teams = useTeams(userId);
  const [week, setWeek] = useState<number | null>(null);
  const [team, setTeam] = useState<string | null>(null);
  const [mine, setMine] = useState(false);
  const [picking, setPicking] = useState(false);
  const chips = useRef<ComponentRef<typeof ScrollView>>(null);

  const selectedWeek = week ?? season.data?.current_week ?? null;
  const available = season.data?.schedule_available === true && selectedWeek !== null;
  const games = useAllGames(
    userId,
    { week: selectedWeek ?? undefined, team: team ?? undefined, favorites: mine || undefined },
    available,
  );
  const { hasNextPage, isFetchingNextPage, fetchNextPage } = games;
  useEffect(() => {
    if (hasNextPage && !isFetchingNextPage) void fetchNextPage();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);
  const [now] = useState(() => new Date().toISOString());
  const teamNext = useGames(userId, { team: team ?? undefined, from: now, limit: 1 }, !!team);
  const [refreshing, setRefreshing] = useState(false);

  const weeks = season.data?.weeks ?? [];
  const weekIndex = weeks.findIndex((w) => w.week === selectedWeek);
  useEffect(() => {
    if (weekIndex > 0) chips.current?.scrollTo({ x: (weekIndex - 1) * CHIP_STEP, animated: false });
  }, [weekIndex]);

  const days = useMemo(() => {
    const items = games.data?.pages.flatMap((p) => p.items) ?? [];
    const groups = new Map<string, typeof items>();
    for (const game of items) {
      const key = gameDayKey(game, timeZone);
      groups.set(key, [...(groups.get(key) ?? []), game]);
    }
    return [...groups.entries()];
  }, [games.data, timeZone]);

  const teamName = teams.data?.find((t) => t.id === team)?.nickname;
  const weekLabel = weeks[weekIndex]?.label ?? "";

  const refresh = async () => {
    setRefreshing(true);
    await Promise.all([season.refetch(), games.refetch()]);
    setRefreshing(false);
  };

  let body;
  if (season.isPending || (available && games.isPending)) {
    body = <Skeleton rows={5} height={72} />;
  } else if (season.isError && !season.data) {
    body = <ErrorState error={season.error} onRetry={() => void season.refetch()} />;
  } else if (!season.data?.schedule_available) {
    body = (
      <EmptyState
        icon="calendar-blank"
        title={COPY.scheduleNotOut}
        body={COPY.scheduleNotOutDetail}
      />
    );
  } else if (games.isError && !games.data) {
    body = <ErrorState error={games.error} onRetry={() => void games.refetch()} />;
  } else if (days.length === 0) {
    const nextGame = teamNext.data?.items[0];
    const playoffs = (selectedWeek ?? 0) > REGULAR_SEASON_WEEKS;
    body =
      team && !mine ? (
        <EmptyState
          icon="sofa-outline"
          title={
            playoffs
              ? `The ${teamName ?? team} don't play in the ${titleCase(weekLabel)} round.`
              : `The ${teamName ?? team} have a bye in ${titleCase(weekLabel)}.`
          }
          action={
            nextGame ? { label: "Next game ›", onPress: () => onOpenGame(nextGame.id) } : undefined
          }
        />
      ) : (
        <EmptyState
          icon="calendar-remove-outline"
          title={`None of your teams play in ${titleCase(weekLabel)}.`}
          body="Turn off My teams to see every game."
        />
      );
  } else {
    body = days.map(([day, dayGames]) => (
      <View key={day} style={styles.day}>
        <Text style={[type.label, styles.dayHeader]} accessibilityRole="header">
          {formatDayHeader(day)}
        </Text>
        <CardGrid>
          {dayGames.map((game) => (
            <GameCard
              key={game.id}
              game={game}
              timeZone={timeZone}
              compact
              onPress={() => onOpenGame(game.id)}
            />
          ))}
        </CardGrid>
      </View>
    ));
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
      <SectionTitle>SCHEDULE</SectionTitle>
      {weeks.length > 0 ? (
        <ScrollView
          ref={chips}
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.chips}
          accessibilityLabel="Weeks"
        >
          {weeks.map((w) => (
            <Chip
              key={w.week}
              selected={w.week === selectedWeek}
              showSelectedOverlay
              onPress={() => setWeek(w.week)}
              style={[styles.chip, w.week === selectedWeek && styles.chipOn]}
              // Text on the orange fill is dark (UI/UX §4: never white on primary).
              textStyle={[type.label, w.week === selectedWeek && { color: colors.onPrimary }]}
              accessibilityLabel={titleCase(w.label)}
            >
              {w.label.replace("WEEK ", "WK ")}
            </Chip>
          ))}
        </ScrollView>
      ) : null}
      <View style={styles.filters}>
        <Chip
          icon="filter-variant"
          selected={!!team}
          onPress={() => setPicking(true)}
          onClose={team ? () => setTeam(null) : undefined}
          closeIcon="close"
          textStyle={type.label}
          accessibilityLabel={team ? `Team filter: ${teamName ?? team}` : "Filter by team"}
        >
          {team ? (teamName ?? team).toUpperCase() : "ALL TEAMS"}
        </Chip>
        <Chip
          selected={mine}
          showSelectedOverlay
          onPress={() => setMine(!mine)}
          textStyle={type.label}
          accessibilityRole="switch"
          accessibilityState={{ checked: mine }}
        >
          MY TEAMS
        </Chip>
      </View>
      {body}
      <Portal>
        <Modal
          visible={picking}
          onDismiss={() => setPicking(false)}
          contentContainerStyle={styles.sheet}
        >
          <ScrollView>
            <TeamPicker
              teams={teams.data ?? []}
              selected={team ? [team] : []}
              single
              onChange={(ids) => {
                setTeam(ids[0] ?? null);
                setPicking(false);
              }}
            />
          </ScrollView>
          <Button onPress={() => setPicking(false)}>Close</Button>
        </Modal>
      </Portal>
    </Screen>
  );
}

function titleCase(label: string): string {
  return label
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace("Conf.", "Conference");
}

const styles = StyleSheet.create({
  chips: { gap: spacing.sm, paddingVertical: spacing.xs },
  chip: { minWidth: 80, backgroundColor: colors.surface },
  chipOn: { backgroundColor: colors.primary },
  filters: { flexDirection: "row", gap: spacing.sm, flexWrap: "wrap" },
  day: { gap: spacing.sm },
  dayHeader: { color: colors.text },
  sheet: {
    backgroundColor: colors.surfaceRaised,
    margin: spacing.lg,
    padding: spacing.lg,
    maxHeight: "85%",
    maxWidth: 520,
    alignSelf: "center",
    width: "92%",
  },
});
