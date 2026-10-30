import { MaterialCommunityIcons } from "@expo/vector-icons";
import { createContext, useContext, type ComponentProps } from "react";
import { Platform, type ColorValue, type ViewStyle } from "react-native";

import { colors, fontFamily } from "./theme/tokens";

type IconName = ComponentProps<typeof MaterialCommunityIcons>["name"];

/** The four primary destinations (UI/UX §2.2). */
export const TABS: { name: string; title: string; icon: IconName }[] = [
  { name: "home", title: "Home", icon: "home-outline" },
  { name: "schedule", title: "Schedule", icon: "calendar-month-outline" },
  { name: "plan", title: "Plan", icon: "map-marker-path" },
  { name: "my-game-days", title: "My Game Days", icon: "bookmark-outline" },
];

/** Pages inside the tab navigator without a tab of their own, so the bottom tabs (or the side
 * navigation on wide web) stay on screen there too (UI/UX §2.2). */
export const PAGES_WITHOUT_TAB = ["games/[id]", "settings", "inbox"] as const;

/** Options for those pages: no button in the tab bar. (`href: null` would hide the route itself,
 * and Expo Router redirects away from hidden tabs.) */
export const pageWithoutTabOptions = {
  tabBarButton: () => null,
  tabBarItemStyle: { display: "none" as const },
};

export function tabIcon(icon: IconName) {
  function TabIcon({ color, size }: { color: ColorValue; size: number }) {
    return <MaterialCommunityIcons name={icon} color={color as string} size={size} />;
  }
  return TabIcon;
}

/** Height of the bottom tab bar above the device's bottom safe area. */
export const TAB_BAR_HEIGHT = 60;

/** Navigation glass: see-through over the background photo, blurred where supported (web). */
export const navGlass: ViewStyle = {
  backgroundColor: colors.navGlass,
  ...(Platform.OS === "web" ? ({ backdropFilter: "blur(12px)" } as ViewStyle) : null),
};

// The space a floating bottom tab bar covers at the bottom of each page, so `Screen` can keep
// its last content clear of it. Zero where there's no bottom bar (wide web).
const TabBarSpace = createContext(0);
export const TabBarSpaceProvider = TabBarSpace.Provider;
export function useTabBarSpace(): number {
  return useContext(TabBarSpace);
}

/**
 * Bottom tabs on phones and narrow web: a glass bar floating over the page's photo, with an
 * orange tint behind the active tab. On web at ≥ 1024 px the app layout shows `SideNav` beside
 * every page instead and the tab bar is hidden; scenes are then transparent so the one photo
 * behind the side navigation and the page shows through (`transparentScenes`). Inactive tabs stay
 * mounted underneath, so they fade out rather than relying on an opaque page to cover them.
 */
export function tabScreenOptions({
  bottomInset,
  transparentScenes = false,
}: {
  bottomInset: number;
  transparentScenes?: boolean;
}) {
  return {
    headerShown: false,
    tabBarActiveTintColor: colors.primary,
    tabBarInactiveTintColor: colors.textMuted,
    tabBarActiveBackgroundColor: colors.navActive,
    tabBarStyle: {
      ...navGlass,
      position: "absolute" as const,
      height: TAB_BAR_HEIGHT + bottomInset,
      borderTopColor: colors.outline,
    },
    tabBarLabelStyle: {
      fontFamily: fontFamily.headingMedium,
      textTransform: "uppercase" as const,
      letterSpacing: 0.5,
    },
    sceneStyle: { backgroundColor: transparentScenes ? "transparent" : colors.background },
    ...(transparentScenes ? { animation: "fade" as const } : null),
  };
}
