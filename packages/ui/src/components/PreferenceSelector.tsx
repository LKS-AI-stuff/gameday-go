import type { Option } from "@gamedaygo/shared";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { SegmentedButtons } from "react-native-paper";

import { colors, layout, spacing, type } from "../theme/tokens";

interface PreferenceSelectorProps<T extends string> {
  label: string;
  options: Option<T>[];
  value: T;
  onChange: (value: T) => void;
  /** Option cards instead of segmented buttons (viewing preference, UI/UX §7.2). */
  cards?: boolean;
}

/** Segmented choice with a one-line helper for the selected option (UI/UX §6.8). */
export function PreferenceSelector<T extends string>({
  label,
  options,
  value,
  onChange,
  cards = false,
}: PreferenceSelectorProps<T>) {
  const selected = options.find((o) => o.value === value);
  return (
    <View style={styles.selector} accessibilityLabel={label}>
      {cards ? (
        <View style={styles.cards} accessibilityRole="radiogroup">
          {options.map((option) => {
            const on = option.value === value;
            return (
              <Pressable
                key={option.value}
                onPress={() => onChange(option.value)}
                accessibilityRole="radio"
                accessibilityState={{ selected: on }}
                accessibilityLabel={`${option.label}. ${option.helper}`}
                style={[styles.card, on && styles.cardOn]}
              >
                <Text style={[type.label, { color: on ? colors.primaryText : colors.text }]}>
                  {option.label}
                </Text>
                <Text style={[type.caption, { color: colors.textMuted }]}>{option.helper}</Text>
              </Pressable>
            );
          })}
        </View>
      ) : (
        <>
          <SegmentedButtons
            value={value}
            onValueChange={(v) => onChange(v as T)}
            buttons={options.map((o) => ({
              value: o.value,
              label: o.label,
              accessibilityLabel: o.label,
            }))}
          />
          {selected ? (
            <Text style={[type.body, { color: colors.textMuted }]} accessibilityLiveRegion="polite">
              {selected.helper}
            </Text>
          ) : null}
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  selector: { gap: spacing.md },
  cards: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  card: {
    flexBasis: "47%",
    flexGrow: 1,
    minHeight: layout.minTouchTarget * 2,
    padding: spacing.md,
    gap: spacing.xs,
    borderWidth: 1,
    borderColor: colors.outline,
    backgroundColor: colors.surface,
  },
  cardOn: { borderColor: colors.primaryText },
});
