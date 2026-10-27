import type { ExpoConfig } from "expo/config";

const config: ExpoConfig = {
  name: "GameDay Go",
  slug: "gameday-go-web",
  version: "0.1.0",
  scheme: "gamedaygo",
  // One dark theme everywhere (NFR-5): native chrome (keyboard, dialogs) stays dark too.
  userInterfaceStyle: "dark",
  backgroundColor: "#111111",
  web: {
    // A single-page app; in M6 the API serves it with an SPA fallback (TDD §18).
    output: "single",
    bundler: "metro",
  },
  plugins: ["expo-router", "expo-font"],
  experiments: {
    typedRoutes: true,
  },
};

export default config;
