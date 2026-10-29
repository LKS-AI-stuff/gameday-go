import { ApiError, usePreferences, useGame } from "@gamedaygo/api-client";
import { COPY, tagExplanation, tagLabel, TRAVEL_OPTIONS } from "@gamedaygo/shared";
import { useState } from "react";
import { RefreshControl, StyleSheet, Text, View } from "react-native";
import { Button } from "react-native-paper";

import { MatchupHero } from "../components/MatchupHero";
import { FreshnessLine, PlanningWindowNotice, TravelHint } from "../components/Notices";
import { Panel, SectionTitle } from "../components/Panel";
import { Screen } from "../components/Screen";
import {
  EmptyState,
  ErrorState,
  isOffline,
  OfflineBanner,
  Skeleton,
} from "../components/StateViews";
import { useViewer } from "../hooks/useViewer";
import { colors, spacing, type } from "../theme/tokens";

interface GameDetailScreenProps {
  gameId: string;
  onBack: () => void;
}

/** UI/UX §7.5. Tickets and bars arrive in M2, planning in M3, alerts in M5, scores in M4. */
export function GameDetailScreen({ gameId, onBack }: GameDetailScreenProps) {
  const { userId, timeZone } = useViewer();
  const game = useGame(userId, gameId);
  const preferences = usePreferences(userId);
  const [refreshing, setRefreshing] = useState(false);

  if (game.isPending) {
    return (
      <Screen>
        <Skeleton rows={3} height={120} />
      </Screen>
    );
  }
  if (game.isError && !game.data) {
    const missing = game.error instanceof ApiError && game.error.status === 404;
    return (
      <Screen>
        {missing ? (
          <EmptyState
            icon="calendar-question"
            title="This game isn't on the schedule anymore."
            action={{ label: "Back to schedule", onPress: onBack }}
          />
        ) : (
          <ErrorState error={game.error} onRetry={() => void game.refetch()} />
        )}
      </Screen>
    );
  }

  const g = game.data;
  const travelLevel = TRAVEL_OPTIONS.find((o) => o.value === preferences.data?.travel)?.label;

  const plan = (
    <Panel variant="glass">
      {g.planning.status === "open" ? (
        <>
          <Button mode="contained" disabled accessibilityHint={COPY.planningSoon}>
            Plan this game
          </Button>
          <Text style={[type.caption, { color: colors.textMuted }]}>{COPY.planningSoon}</Text>
        </>
      ) : g.planning.status === "opens_on" && g.planning.opens_at ? (
        <PlanningWindowNotice opensAt={g.planning.opens_at} timeZone={timeZone} />
      ) : (
        <Text style={[type.body, { color: colors.textMuted }]}>
          {g.status === "cancelled" ? "This game was cancelled." : "This game has been played."}
        </Text>
      )}
      {g.travel_hint === "outside_travel_area" && travelLevel ? (
        <TravelHint level={travelLevel} />
      ) : null}
    </Panel>
  );

  const about = (
    <Panel variant="glass" style={styles.about}>
      <SectionTitle>ABOUT THIS GAME</SectionTitle>
      <Text style={[type.body, { color: colors.text }]}>
        {g.stage === "playoff"
          ? `${titleCase(g.week_label)}, playoffs`
          : `${titleCase(g.week_label)}, regular season`}
      </Text>
      {g.venue_name ? (
        <Text style={[type.body, { color: colors.textMuted }]}>
          {g.venue_name}
          {g.venue_city ? `, ${[g.venue_city, g.venue_state].filter(Boolean).join(", ")}` : ""}
        </Text>
      ) : null}
      {g.tags.map((t) => (
        <View key={t.tag} style={styles.tagLine}>
          <Text style={[type.label, { color: colors.text }]}>{tagLabel(t.tag)}</Text>
          <Text style={[type.body, { color: colors.textMuted }]}>
            {tagExplanation(t.tag, t.detail)}
          </Text>
        </View>
      ))}
      <FreshnessLine
        source={g.source.provider}
        updatedAt={g.source.schedule_updated_at}
        timeZone={timeZone}
        what="schedule updated"
      />
    </Panel>
  );

  return (
    <Screen
      heroBand
      hero={<MatchupHero game={g} timeZone={timeZone} onBack={onBack} />}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => {
            setRefreshing(true);
            void game.refetch().finally(() => setRefreshing(false));
          }}
          tintColor={colors.text}
        />
      }
    >
      <OfflineBanner visible={isOffline(game)} />
      {/* One column until M2 adds Tickets and Bars as the desktop right column (UI/UX §7.5). */}
      {plan}
      {about}
    </Screen>
  );
}

function titleCase(label: string): string {
  return label.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
}

const styles = StyleSheet.create({
  about: { gap: spacing.md },
  tagLine: { gap: spacing.xs },
});
