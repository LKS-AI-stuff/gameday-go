import { useEffect, useRef, useState, type ComponentRef } from "react";
import {
  Platform,
  ScrollView,
  StyleSheet,
  View,
  type LayoutChangeEvent,
  type NativeScrollEvent,
  type NativeSyntheticEvent,
} from "react-native";
import { Chip, IconButton } from "react-native-paper";

import { colors, spacing, type } from "../theme/tokens";

const CHIP_STEP = 96;
/** An arrow press scrolls this share of the visible row, keeping a chip or two for context. */
const PAGE_SHARE = 0.8;

interface WeekChipsProps {
  weeks: { week: number; label: string }[];
  selected: number | null;
  onSelect: (week: number) => void;
  /** Accessible name for each chip, e.g. "Week 11". */
  chipLabel: (label: string) => string;
}

/**
 * The schedule's week chips in one scrolling row (UI/UX §7.4). Phones swipe it. On web, ‹ ›
 * buttons scroll it a screenful at a time and the mouse wheel scrolls it sideways, since a
 * mouse can't swipe and the row's scrollbar is hidden.
 */
export function WeekChips({ weeks, selected, onSelect, chipLabel }: WeekChipsProps) {
  const row = useRef<ComponentRef<typeof ScrollView>>(null);
  const [x, setX] = useState(0);
  const [viewport, setViewport] = useState(0);
  const [content, setContent] = useState(0);
  const web = Platform.OS === "web";

  const index = weeks.findIndex((w) => w.week === selected);
  useEffect(() => {
    // Bring the selected week into view, with the week before it for context.
    if (index > 0) row.current?.scrollTo({ x: (index - 1) * CHIP_STEP, animated: false });
  }, [index]);

  useEffect(() => {
    if (!web) return;
    const node = (
      row.current as unknown as { getScrollableNode?: () => HTMLElement | null }
    )?.getScrollableNode?.();
    if (!node) return;
    const onWheel = (e: WheelEvent) => {
      // Turn vertical wheel movement into sideways scrolling while the row can scroll.
      if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
      if (node.scrollWidth <= node.clientWidth) return;
      e.preventDefault();
      node.scrollLeft += e.deltaY;
    };
    node.addEventListener("wheel", onWheel, { passive: false });
    return () => node.removeEventListener("wheel", onWheel);
  }, [web]);

  const page = (direction: -1 | 1) => {
    const max = Math.max(0, content - viewport);
    const target = Math.min(max, Math.max(0, x + direction * viewport * PAGE_SHARE));
    row.current?.scrollTo({ x: target, animated: true });
  };
  const atStart = x <= 1;
  const atEnd = x >= content - viewport - 1;

  return (
    <View style={styles.wrap}>
      {web ? (
        <IconButton
          icon="chevron-left"
          iconColor={colors.text}
          onPress={() => page(-1)}
          disabled={atStart}
          accessibilityLabel="Earlier weeks"
          style={styles.arrow}
        />
      ) : null}
      <ScrollView
        ref={row}
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.chips}
        accessibilityLabel="Weeks"
        style={styles.row}
        scrollEventThrottle={16}
        onScroll={(e: NativeSyntheticEvent<NativeScrollEvent>) =>
          setX(e.nativeEvent.contentOffset.x)
        }
        onLayout={(e: LayoutChangeEvent) => setViewport(e.nativeEvent.layout.width)}
        onContentSizeChange={(width) => setContent(width)}
      >
        {weeks.map((w) => (
          <Chip
            key={w.week}
            selected={w.week === selected}
            showSelectedOverlay
            onPress={() => onSelect(w.week)}
            style={[styles.chip, w.week === selected && styles.chipOn]}
            // Text on the orange fill is dark (UI/UX §4: never white on primary).
            textStyle={[type.label, w.week === selected && { color: colors.onPrimary }]}
            accessibilityLabel={chipLabel(w.label)}
          >
            {w.label.replace("WEEK ", "WK ")}
          </Chip>
        ))}
      </ScrollView>
      {web ? (
        <IconButton
          icon="chevron-right"
          iconColor={colors.text}
          onPress={() => page(1)}
          disabled={atEnd}
          accessibilityLabel="Later weeks"
          style={styles.arrow}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { flexDirection: "row", alignItems: "center" },
  row: { flex: 1 },
  arrow: { margin: 0 },
  chips: { gap: spacing.sm, paddingVertical: spacing.xs },
  chip: { minWidth: 80, backgroundColor: colors.surface },
  chipOn: { backgroundColor: colors.primary },
});
