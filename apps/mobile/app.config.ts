import type { ExpoConfig } from "expo/config";

const config: ExpoConfig = {
  name: "GameDay Go",
  slug: "gameday-go",
  version: "0.1.0",
  scheme: "gamedaygo",
  orientation: "portrait",
  // Native only: the web app is apps/web. Without this, opening the dev server URL in a
  // browser serves this app as a website, where SecureStore does not exist.
  platforms: ["ios", "android"],
  userInterfaceStyle: "automatic",
  ios: {
    bundleIdentifier: "com.gamedaygo.app",
    supportsTablet: true,
  },
  android: {
    package: "com.gamedaygo.app",
  },
  plugins: ["expo-router", "expo-font", "expo-secure-store", "expo-splash-screen"],
  experiments: {
    typedRoutes: true,
  },
};

export default config;
