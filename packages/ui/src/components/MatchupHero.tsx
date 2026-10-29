import type { GameDetail } from "@gamedaygo/api-client";
import { formatDistance, formatKickoff, type TagWeight } from "@gamedaygo/shared";
import { Platform, StyleSheet, Text, View } from "react-native";
import { IconButton } from "react-native-paper";

import { colors, displayWeb, spacing, type } from "../theme/tokens";
import { SampleDataBadge } from "./Notices";
import { TagRow } from "./TagChip";

/** "SUNDAY NIGHT" for primetime games; the slot is defined in Eastern time (BRD §7.6). */
function nightLabel(kickoffAt: string): string {
  const weekday = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    weekday: "long",
  }).format(new Date(kickoffAt));
  return `${weekday} night`.toUpperCase();
}

/** Game detail header on the black field-line band (UI/UX §6.2). Records arrive in M4. */
export function MatchupHero({
  game,
  timeZone,
  onBack,
}: {
  game: GameDetail;
  timeZone: string;
  onBack: () => void;
}) {
  const display = Platform.OS === "web" ? displayWeb : type.display;
  const night =
    game.kickoff_at && game.tags.some((t) => t.tag === "primetime")
      ? nightLabel(game.kickoff_at)
      : undefined;
  const place = [game.venue_name, [game.venue_city, game.venue_state].filter(Boolean).join(", ")]
    .filter(Boolean)
    .join(" · ");
  const distance = game.distance_mi != null ? ` · ${formatDistance(game.distance_mi)}` : "";

  return (
    <View style={styles.hero}>
      <IconButton
        icon="arrow-left"
        iconColor={colors.text}
        onPress={onBack}
        accessibilityLabel="Back"
        style={styles.back}
      />
      <View style={styles.titleRow}>
        <Text style={[type.label, { color: colors.textMuted }]}>
          {[game.week_label, night].filter(Boolean).join(" · ")}
        </Text>
        {game.is_sample ? <SampleDataBadge /> : null}
      </View>
      <Text style={[display, { color: colors.text }]} accessibilityRole="header">
        {(game.away?.nickname ?? game.away_placeholder ?? "TBD").toUpperCase()}
        {"\n"}
        <Text style={{ color: colors.textSubtle }}>@ </Text>
        {(game.home?.nickname ?? game.home_placeholder ?? "TBD").toUpperCase()}
      </Text>
      <Text style={[type.label, { color: colors.text }]}>{formatKickoff(game, timeZone)}</Text>
      {place ? (
        <Text style={[type.body, { color: colors.textMuted }]}>
          {place}
          {distance}
        </Text>
      ) : null}
      <TagRow tags={game.tags.map((t) => ({ ...t, weight: t.weight as TagWeight }))} max={6} />
    </View>
  );
}

const styles = StyleSheet.create({
  hero: { gap: spacing.sm },
  back: { marginLeft: -spacing.md, marginBottom: spacing.sm },
  titleRow: { flexDirection: "row", gap: spacing.sm, alignItems: "center" },
});
