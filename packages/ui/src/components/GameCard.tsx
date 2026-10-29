import type { GameSummary } from "@gamedaygo/api-client";
import {
  COPY,
  formatDistance,
  formatKickoff,
  formatMatchup,
  tagLabel,
  type TagWeight,
} from "@gamedaygo/shared";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { Icon } from "react-native-paper";

import { colors, layout, spacing, type } from "../theme/tokens";
import { PlanningWindowNotice, SampleDataBadge } from "./Notices";
import { TagRow } from "./TagChip";

const STATUS_PILLS: Record<string, { label: string; color: string; icon: string }> = {
  postponed: { label: "POSTPONED", color: colors.danger, icon: "calendar-remove" },
  cancelled: { label: "CANCELLED", color: colors.danger, icon: "cancel" },
  final: { label: "FINAL", color: colors.textMuted, icon: "flag-checkered" },
  final_ot: { label: "FINAL/OT", color: colors.textMuted, icon: "flag-checkered" },
};

function venueLine(game: GameSummary): string {
  const place = [game.venue_city, game.venue_state].filter(Boolean).join(", ");
  return [game.venue_name, place].filter(Boolean).join(" · ");
}

/** One read-out for screen readers (UI/UX §6.1). */
export function gameAccessibilityLabel(game: GameSummary, timeZone: string): string {
  const away = game.away?.nickname ?? game.away_placeholder ?? "TBD";
  const home = game.home?.nickname ?? game.home_placeholder ?? "TBD";
  const parts = [
    `${away} at ${home}`,
    formatKickoff(game, timeZone, "sentence"),
    venueLine(game),
    ...game.tags.map((t) => tagLabel(t.tag).toLowerCase()),
  ];
  const pill = STATUS_PILLS[game.status];
  if (pill) parts.push(pill.label.toLowerCase());
  return parts.filter(Boolean).join(", ");
}

function StatusPill({ status }: { status: string }) {
  const pill = STATUS_PILLS[status];
  if (!pill) return null;
  return (
    <View style={[styles.pill, { borderColor: pill.color }]}>
      <Icon source={pill.icon} size={14} color={pill.color} />
      <Text style={[type.label, styles.pillText, { color: pill.color }]}>{pill.label}</Text>
    </View>
  );
}

interface GameCardProps {
  game: GameSummary;
  timeZone: string;
  onPress: () => void;
  /** Schedule rows: single-line matchup, tag dots (UI/UX §7.4). */
  compact?: boolean;
}

/** The template's "upcoming match" card (UI/UX §6.1). Live, final-score and saved variants
 * arrive with scores (M4) and saved plans (M3). */
export function GameCard({ game, timeZone, onPress, compact = false }: GameCardProps) {
  const tbdTeams = !game.home || !game.away;
  const tags = (tbdTeams ? game.tags.filter((t) => t.tag === "playoff") : game.tags).map((t) => ({
    ...t,
    weight: t.weight as TagWeight,
  }));
  const kickoffStruck = game.status === "postponed" || game.status === "cancelled";

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={gameAccessibilityLabel(game, timeZone)}
      style={({ pressed }) => [styles.card, compact && styles.compact, pressed && styles.pressed]}
    >
      <View style={styles.header}>
        <Text style={[type.label, { color: colors.textMuted }, kickoffStruck && styles.struck]}>
          {formatKickoff(game, timeZone)}
        </Text>
        <View style={styles.headerRight}>
          {game.is_sample ? <SampleDataBadge /> : null}
          <StatusPill status={game.status} />
        </View>
      </View>

      {compact ? (
        <Text style={[type.h3, { color: colors.text }]} numberOfLines={2}>
          {formatMatchup(game.away, game.home, game.away_placeholder, game.home_placeholder)}
        </Text>
      ) : (
        <View>
          <Text style={[type.h3, { color: colors.text }]}>
            {(game.away?.nickname ?? game.away_placeholder ?? "TBD").toUpperCase()}
          </Text>
          <Text style={[type.h3, { color: colors.text }]}>
            <Text style={{ color: colors.textSubtle }}>@ </Text>
            {(game.home?.nickname ?? game.home_placeholder ?? "TBD").toUpperCase()}
          </Text>
        </View>
      )}

      {venueLine(game) ? (
        <Text style={[type.body, { color: colors.textMuted }]} numberOfLines={1}>
          {venueLine(game)}
        </Text>
      ) : null}

      {compact ? (
        tags.length ? (
          <View style={styles.dots} accessibilityElementsHidden>
            {tags.map((t) => (
              <View
                key={t.tag}
                style={[
                  styles.dot,
                  { backgroundColor: t.weight === "high" ? colors.primaryText : colors.textSubtle },
                ]}
              />
            ))}
          </View>
        ) : null
      ) : (
        <TagRow tags={tags} interactive={false} />
      )}

      {compact ? null : (
        <View style={styles.footer}>
          <Text style={[type.caption, { color: colors.textMuted }]}>
            {game.distance_mi !== null && game.distance_mi !== undefined
              ? `${formatDistance(game.distance_mi)} away`
              : ""}
          </Text>
          {game.planning.status === "open" ? (
            <View style={styles.planAction} accessibilityState={{ disabled: true }}>
              <Text style={[type.label, { color: colors.textSubtle }]}>PLAN THIS GAME</Text>
              <Text style={[type.caption, { color: colors.textSubtle }]}>{COPY.planningSoon}</Text>
            </View>
          ) : game.planning.status === "opens_on" && game.planning.opens_at ? (
            <PlanningWindowNotice opensAt={game.planning.opens_at} timeZone={timeZone} />
          ) : null}
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.panelGlass,
    borderWidth: 1,
    borderColor: colors.outline,
    padding: spacing.lg,
    gap: spacing.sm,
    minHeight: layout.minTouchTarget,
    flexGrow: 1,
  },
  compact: { paddingVertical: spacing.md },
  pressed: { borderColor: colors.outlineStrong },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  headerRight: { flexDirection: "row", gap: spacing.sm, alignItems: "center" },
  struck: { textDecorationLine: "line-through" },
  pill: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
    borderWidth: 1,
    paddingHorizontal: spacing.sm,
  },
  pillText: { fontSize: 11, lineHeight: 16 },
  dots: { flexDirection: "row", gap: spacing.xs },
  dot: { width: 8, height: 8, borderRadius: 4 },
  footer: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderTopWidth: 1,
    borderTopColor: colors.outline,
    paddingTop: spacing.sm,
    gap: spacing.sm,
    flexWrap: "wrap",
  },
  planAction: { alignItems: "flex-end" },
});
