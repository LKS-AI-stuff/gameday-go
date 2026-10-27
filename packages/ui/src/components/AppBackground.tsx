import type { ReactNode } from "react";
import { ImageBackground, StyleSheet, useWindowDimensions, View } from "react-native";

import { colors } from "../theme/tokens";

// Night stadium photo behind every screen (UI/UX §4), in two crops of the same scene: tall for
// phones and narrow windows, wide for landscape screens, so the whole scene shows on both.
// The upper area is dark enough for text; the bright parts are not, so body content sits on panels.
const STADIUM_NIGHT = require("../../assets/stadium-night.jpg");
const STADIUM_NIGHT_WIDE = require("../../assets/stadium-night-wide.jpg");

/** Fixed full-screen background: the photo under a light scrim, on the dark base color. */
export function AppBackground({ children }: { children: ReactNode }) {
  const { width, height } = useWindowDimensions();
  const wide = width > height;
  return (
    <ImageBackground
      source={wide ? STADIUM_NIGHT_WIDE : STADIUM_NIGHT}
      style={styles.fill}
      resizeMode="cover"
      // On web the image otherwise keeps the file's pixel size and stops short on big screens.
      imageStyle={styles.image}
      accessibilityIgnoresInvertColors
      testID={wide ? "app-background-wide" : "app-background"}
    >
      <View
        style={[StyleSheet.absoluteFill, { backgroundColor: colors.scrim }]}
        pointerEvents="none"
      />
      {children}
    </ImageBackground>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1, backgroundColor: colors.background },
  image: { width: "100%", height: "100%" },
});
