import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useEffect, useState, type ComponentProps } from "react";
import { Animated, Pressable, StyleSheet, Text, View } from "react-native";

import { navGlass } from "../navigation";
import { colors, fontFamily, motion, spacing } from "../theme/tokens";
import { Wordmark } from "./Brand";

type IconName = ComponentProps<typeof MaterialCommunityIcons>["name"];

const PANEL_WIDTH = 240;
const HANDLE_WIDTH = 28;
const HANDLE_HEIGHT = 64;

export interface SideNavProps {
  items: { name: string; title: string; icon: IconName }[];
  /** The item for the current page, if any (none on game detail, Settings, Inbox). */
  current: string | null;
  onNavigate: (name: string) => void;
}

/**
 * Primary navigation on wide web (UI/UX §2.2): a left column beside every signed-in page. Open
 * when the app loads; the orange tab on its edge slides it shut so the page and its background
 * photo take the full width, and back open. It stays as set while moving between pages.
 */
export function SideNav({ items, current, onNavigate }: SideNavProps) {
  const [open, setOpen] = useState(true);
  const [progress] = useState(() => new Animated.Value(1));

  useEffect(() => {
    // Width can't use the native driver; the column is only used on web.
    Animated.timing(progress, {
      toValue: open ? 1 : 0,
      duration: motion.enterMs,
      useNativeDriver: false,
    }).start();
  }, [open, progress]);

  const width = progress.interpolate({ inputRange: [0, 1], outputRange: [0, PANEL_WIDTH] });

  return (
    <Animated.View style={[styles.column, { width }]}>
      {/* Clipped while it slides. While shut, the items ignore screen readers and keyboard
          focus; only the handle stays reachable. */}
      <View
        style={styles.clip}
        accessibilityRole="menu"
        aria-hidden={!open}
        accessibilityElementsHidden={!open}
        importantForAccessibility={open ? "auto" : "no-hide-descendants"}
      >
        <View style={styles.items}>
          <View style={styles.header}>
            <Wordmark size="compact" />
          </View>
          {items.map((item) => {
            const selected = item.name === current;
            const color = selected ? colors.primary : colors.textMuted;
            return (
              <Pressable
                key={item.name}
                onPress={() => onNavigate(item.name)}
                accessibilityRole="link"
                accessibilityLabel={item.title}
                accessibilityState={{ selected }}
                focusable={open}
                style={[styles.item, selected ? styles.itemSelected : null]}
              >
                <MaterialCommunityIcons name={item.icon} size={22} color={color} />
                <Text style={[styles.label, { color }]}>{item.title}</Text>
              </Pressable>
            );
          })}
        </View>
      </View>
      <Pressable
        onPress={() => setOpen(!open)}
        accessibilityRole="button"
        accessibilityLabel={open ? "Hide menu" : "Show menu"}
        accessibilityState={{ expanded: open }}
        style={styles.handle}
      >
        <MaterialCommunityIcons
          name={open ? "chevron-left" : "chevron-right"}
          size={24}
          color={colors.onPrimary}
        />
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  // Glass over the one photo behind the navigation and the page (UI/UX §2.2).
  column: {
    ...navGlass,
    borderRightWidth: 1,
    borderRightColor: colors.outline,
    zIndex: 1,
  },
  clip: { flex: 1, overflow: "hidden" },
  items: {
    width: PANEL_WIDTH,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.xl,
    gap: spacing.xs,
  },
  header: { paddingLeft: spacing.md, marginBottom: spacing.lg },
  item: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    minHeight: 48,
    paddingHorizontal: spacing.md,
    borderLeftWidth: 3,
    borderLeftColor: "transparent",
  },
  itemSelected: { borderLeftColor: colors.primary, backgroundColor: colors.navActive },
  label: {
    fontFamily: fontFamily.headingMedium,
    fontSize: 16,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  // The orange tab on the column's edge; it stays at the screen edge when the column is shut.
  handle: {
    position: "absolute",
    top: "50%",
    right: -HANDLE_WIDTH,
    width: HANDLE_WIDTH,
    height: HANDLE_HEIGHT,
    marginTop: -HANDLE_HEIGHT / 2,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.primary,
  },
});
