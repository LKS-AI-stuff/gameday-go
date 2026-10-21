import { useColorScheme } from "react-native";

import { colors, type ColorScheme, type ColorTokens } from "./tokens";

/** The active color scheme. Follows the OS for now; a Settings override comes later (UX3). */
export function useScheme(): ColorScheme {
  return useColorScheme() === "dark" ? "dark" : "light";
}

export function useColors(): ColorTokens {
  return colors[useScheme()];
}
