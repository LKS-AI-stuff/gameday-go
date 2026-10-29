import type { Team } from "@gamedaygo/api-client";
import { useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { Icon, TextInput } from "react-native-paper";

import { colors, layout, spacing, type } from "../theme/tokens";

interface TeamPickerProps {
  teams: Team[];
  selected: string[];
  onChange: (ids: string[]) => void;
  /** Schedule filter: one team at a time. */
  single?: boolean;
}

/** Team tiles grouped by division (8 groups of 4), text only (UI/UX §6.8, NFR-18). */
export function TeamPicker({ teams, selected, onChange, single = false }: TeamPickerProps) {
  const [query, setQuery] = useState("");
  const groups = useMemo(() => {
    const q = query.trim().toLowerCase();
    const matches = teams.filter(
      (t) => !q || t.name.toLowerCase().includes(q) || t.id.toLowerCase() === q,
    );
    const byDivision = new Map<string, Team[]>();
    for (const team of matches) {
      const key = `${team.conference} ${team.division}`;
      byDivision.set(key, [...(byDivision.get(key) ?? []), team]);
    }
    return [...byDivision.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [teams, query]);

  const toggle = (id: string) => {
    if (single) onChange(selected.includes(id) ? [] : [id]);
    else onChange(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]);
  };

  return (
    <View style={styles.picker}>
      <TextInput
        mode="outlined"
        dense
        placeholder="Search teams"
        accessibilityLabel="Search teams"
        value={query}
        onChangeText={setQuery}
        left={<TextInput.Icon icon="magnify" />}
      />
      {groups.length === 0 ? (
        <Text style={[type.body, { color: colors.textMuted }]}>No team matches that search.</Text>
      ) : null}
      {groups.map(([division, members]) => (
        <View key={division} style={styles.group}>
          <Text style={[type.label, { color: colors.textMuted }]} accessibilityRole="header">
            {division}
          </Text>
          <View style={styles.tiles}>
            {members.map((team) => {
              const on = selected.includes(team.id);
              return (
                <Pressable
                  key={team.id}
                  onPress={() => toggle(team.id)}
                  accessibilityRole={single ? "radio" : "checkbox"}
                  accessibilityState={single ? { selected: on } : { checked: on }}
                  accessibilityLabel={team.name}
                  style={[styles.tile, on && styles.tileOn]}
                >
                  <Text style={[type.label, { color: on ? colors.primaryText : colors.text }]}>
                    {team.id}
                  </Text>
                  <Text style={[type.caption, { color: colors.textMuted }]} numberOfLines={1}>
                    {team.nickname}
                  </Text>
                  {on ? (
                    <View style={styles.check}>
                      <Icon source="check-circle" size={16} color={colors.primaryText} />
                    </View>
                  ) : null}
                </Pressable>
              );
            })}
          </View>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  picker: { gap: spacing.lg },
  group: { gap: spacing.sm },
  tiles: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  tile: {
    width: 92,
    minHeight: layout.minTouchTarget + 8,
    padding: spacing.sm,
    borderWidth: 1,
    borderColor: colors.outline,
    backgroundColor: colors.surface,
    justifyContent: "center",
  },
  tileOn: { borderColor: colors.primaryText },
  check: { position: "absolute", top: spacing.xs, right: spacing.xs },
});
