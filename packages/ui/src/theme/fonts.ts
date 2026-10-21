import { OpenSans_400Regular, OpenSans_600SemiBold } from "@expo-google-fonts/open-sans";
import { Oswald_500Medium, Oswald_600SemiBold, Oswald_700Bold } from "@expo-google-fonts/oswald";
import { useFonts } from "expo-font";

/** Loads the bundled fonts (no runtime call to Google Fonts). Returns true when ready. */
export function useAppFonts(): boolean {
  const [loaded, error] = useFonts({
    Oswald_500Medium,
    Oswald_600SemiBold,
    Oswald_700Bold,
    OpenSans_400Regular,
    OpenSans_600SemiBold,
  });
  // On a font error, render with system fonts rather than blocking the app.
  return loaded || error !== null;
}
