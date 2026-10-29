import { MaterialCommunityIcons } from "@expo/vector-icons";
import type { ComponentProps } from "react";
import type { ColorValue } from "react-native";

import { colors, fontFamily } from "./theme/tokens";

type IconName = ComponentProps<typeof MaterialCommunityIcons>["name"];

/** The four primary destinations (UI/UX §2.2). */
export const TABS: { name: string; title: string; icon: IconName }[] = [
  { name: "home", title: "Home", icon: "home-outline" },
  { name: "schedule", title: "Schedule", icon: "calendar-month-outline" },
  { name: "plan", title: "Plan", icon: "map-marker-path" },
  { name: "my-game-days", title: "My Game Days", icon: "bookmark-outline" },
];

export function tabIcon(icon: IconName) {
  function TabIcon({ color, size }: { color: ColorValue; size: number }) {
    return <MaterialCommunityIcons name={icon} color={color as string} size={size} />;
  }
  return TabIcon;
}

/** Bottom tabs on phones and narrow web; a left rail on web at ≥ 1024 px. */
export function tabScreenOptions(rail: boolean) {
  return {
    headerShown: false,
    tabBarPosition: rail ? ("left" as const) : ("bottom" as const),
    tabBarVariant: rail ? ("material" as const) : ("uikit" as const),
    tabBarActiveTintColor: colors.primary,
    tabBarInactiveTintColor: colors.textMuted,
    tabBarStyle: {
      backgroundColor: colors.chrome,
      borderTopColor: colors.outline,
      borderRightColor: colors.outline,
    },
    tabBarLabelStyle: {
      fontFamily: fontFamily.headingMedium,
      textTransform: "uppercase" as const,
      letterSpacing: 0.5,
    },
    sceneStyle: { backgroundColor: colors.background },
  };
}
