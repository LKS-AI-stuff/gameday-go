import { Children, type ReactNode } from "react";
import { StyleSheet, useWindowDimensions, View } from "react-native";

import { spacing } from "../theme/tokens";

/** 1 column on phones, 2 from 600 px, 3 from 1024 px (UI/UX §3). */
export function CardGrid({ children }: { children: ReactNode }) {
  const { width } = useWindowDimensions();
  const columns = width >= 1024 ? 3 : width >= 600 ? 2 : 1;
  const items = Children.toArray(children);
  if (columns === 1) return <View style={styles.list}>{items}</View>;
  const rows: ReactNode[][] = [];
  for (let i = 0; i < items.length; i += columns) rows.push(items.slice(i, i + columns));
  return (
    <View style={styles.list}>
      {rows.map((row, r) => (
        <View key={r} style={styles.row}>
          {row.map((item, c) => (
            <View key={c} style={styles.cell}>
              {item}
            </View>
          ))}
          {Array.from({ length: columns - row.length }, (_, i) => (
            <View key={`pad-${i}`} style={styles.cell} />
          ))}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  list: { gap: spacing.md },
  row: { flexDirection: "row", gap: spacing.md },
  cell: { flex: 1 },
});
