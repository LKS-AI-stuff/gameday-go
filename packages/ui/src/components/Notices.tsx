import { COPY, formatDateTime, formatPlanningOpens, formatRelative } from "@gamedaygo/shared";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { Icon } from "react-native-paper";

import { colors, spacing, type } from "../theme/tokens";
import { InfoSheet } from "./InfoSheet";

/** "Planning opens on Oct 18." in place of the plan action (FR-SC8, UI/UX §5.2). */
export function PlanningWindowNotice({ opensAt, timeZone }: { opensAt: string; timeZone: string }) {
  return (
    <View style={styles.row}>
      <Icon source="calendar-clock" size={18} color={colors.textMuted} />
      <Text style={[type.caption, { color: colors.textMuted }]}>
        {formatPlanningOpens(opensAt, timeZone)}
      </Text>
    </View>
  );
}

/** "SAMPLE DATA" chip on anything with is_sample (AC-13). */
export function SampleDataBadge() {
  return (
    <View style={styles.sample} accessibilityLabel="Sample data">
      <Text style={[type.label, styles.sampleText]}>SAMPLE DATA</Text>
    </View>
  );
}

interface FreshnessLineProps {
  source: string;
  updatedAt: string | null | undefined;
  timeZone: string;
  what?: string;
  now?: Date;
}

/** `API-Sports · schedule updated 52 min ago`; tap for the exact time (UI/UX §5.1, FR-SC4). */
export function FreshnessLine({
  source,
  updatedAt,
  timeZone,
  what = "updated",
  now = new Date(),
}: FreshnessLineProps) {
  const [open, setOpen] = useState(false);
  const text = updatedAt
    ? `${source} · ${what} ${formatRelative(updatedAt, now, timeZone)}`
    : `${source} · not updated yet`;
  return (
    <>
      <Pressable
        onPress={() => setOpen(true)}
        disabled={!updatedAt}
        accessibilityRole="button"
        accessibilityLabel={`${text}. Show exact time`}
      >
        <Text style={[type.caption, { color: colors.textMuted }]}>{text}</Text>
      </Pressable>
      {updatedAt ? (
        <InfoSheet visible={open} title="Data source" onDismiss={() => setOpen(false)}>
          <Text style={[type.body, { color: colors.textMuted }]}>
            {source}, {what} {formatDateTime(updatedAt, timeZone)}
          </Text>
        </InfoSheet>
      ) : null}
    </>
  );
}

/** Muted travel-rule hint under the hero (UI/UX §7.5). */
export function TravelHint({ level }: { level: string }) {
  return (
    <View style={styles.row}>
      <Icon source="map-marker-distance" size={18} color={colors.textMuted} />
      <Text style={[type.caption, { color: colors.textMuted }]}>
        {COPY.outsideTravelArea(level)}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  sample: {
    borderWidth: 1,
    borderColor: colors.info,
    paddingHorizontal: spacing.sm,
    alignSelf: "flex-start",
  },
  sampleText: { color: colors.info, fontSize: 11, lineHeight: 16 },
});
