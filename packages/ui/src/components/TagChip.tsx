import { tagExplanation, tagLabel, type TagWeight } from "@gamedaygo/shared";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { colors, layout, spacing, type } from "../theme/tokens";
import { InfoSheet } from "./InfoSheet";

interface Tag {
  tag: string;
  weight: TagWeight;
  detail?: string | null;
}

const STYLE_BY_WEIGHT: Record<TagWeight, { border: string; text: string }> = {
  high: { border: colors.primaryText, text: colors.primaryText },
  medium: { border: colors.outlineStrong, text: colors.text },
  info: { border: "transparent", text: colors.textMuted },
};

/** Significance tag, styled by weight; tap for a one-sentence explanation (UI/UX §6.4).
 * Inside a pressable card it's a plain label (`interactive={false}`): a button can't sit
 * inside another button, and the card opens game detail, where tags are explained. */
export function TagChip({
  tag,
  weight,
  detail,
  interactive = true,
}: Tag & { interactive?: boolean }) {
  const [open, setOpen] = useState(false);
  const label = tagLabel(tag);
  const look = STYLE_BY_WEIGHT[weight];
  if (!interactive) {
    return (
      <View style={[styles.chip, { borderColor: look.border }]}>
        <Text style={[type.label, styles.text, { color: look.text }]}>{label}</Text>
      </View>
    );
  }
  return (
    <>
      <Pressable
        onPress={() => setOpen(true)}
        accessibilityRole="button"
        accessibilityLabel={`${label}. Explain this tag`}
        hitSlop={8}
        style={[styles.chip, { borderColor: look.border }]}
      >
        <Text style={[type.label, styles.text, { color: look.text }]}>{label}</Text>
      </Pressable>
      <InfoSheet visible={open} title={label} onDismiss={() => setOpen(false)}>
        <Text style={[type.body, { color: colors.textMuted }]}>{tagExplanation(tag, detail)}</Text>
      </InfoSheet>
    </>
  );
}

/** Up to `max` chips with a "+N" overflow (UI/UX §6.1). */
export function TagRow({
  tags,
  max = 2,
  interactive = true,
}: {
  tags: Tag[];
  max?: number;
  interactive?: boolean;
}) {
  if (tags.length === 0) return null;
  const shown = tags.slice(0, max);
  const more = tags.length - shown.length;
  return (
    <View style={styles.row}>
      {shown.map((t) => (
        <TagChip key={t.tag} {...t} interactive={interactive} />
      ))}
      {more > 0 ? (
        <Text style={[type.label, { color: colors.textMuted }]} accessibilityLabel={`${more} more`}>
          +{more}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    borderWidth: 1,
    paddingHorizontal: spacing.sm,
    minHeight: 28,
    justifyContent: "center",
  },
  text: { fontSize: 12, lineHeight: 16 },
  row: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    alignItems: "center",
    minHeight: layout.minTouchTarget / 2,
  },
});
