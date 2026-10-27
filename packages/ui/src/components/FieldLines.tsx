import { useState } from "react";
import { StyleSheet, View, type LayoutChangeEvent } from "react-native";

import { colors, fieldPattern } from "../theme/tokens";

const SIDELINE_INSET = 0.15; // sidelines at 15% from each edge, as in the mockup
const HASH_WIDTH = 8;
const HASH_GAP = 30;

/**
 * The template's football-field backdrop (UI/UX §4): yard lines, two sidelines and a row of
 * hash marks, in white at low opacity. Purely decorative: hidden from screen readers and
 * touch. Drawn with plain views, so no SVG library is needed.
 */
export function FieldLines() {
  const [size, setSize] = useState({ width: 0, height: 0 });
  const onLayout = (e: LayoutChangeEvent) => {
    const { width, height } = e.nativeEvent.layout;
    if (width !== size.width || height !== size.height) setSize({ width, height });
  };

  const yardCount = Math.floor(size.height / fieldPattern.yardSpacing);
  const hashRow =
    Math.round(yardCount / 2) * fieldPattern.yardSpacing - fieldPattern.yardSpacing / 2;
  const hashCount = Math.max(0, Math.floor((size.width * (1 - 2 * SIDELINE_INSET)) / HASH_GAP) - 1);
  const hashStart = (size.width - (hashCount - 1) * HASH_GAP - HASH_WIDTH) / 2;

  return (
    <View
      style={[StyleSheet.absoluteFill, { opacity: fieldPattern.lineOpacity }]}
      onLayout={onLayout}
      pointerEvents="none"
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      testID="field-lines"
    >
      {Array.from({ length: yardCount }, (_, i) => (
        <View
          key={`yard-${i}`}
          style={[styles.line, styles.yard, { top: (i + 1) * fieldPattern.yardSpacing }]}
        />
      ))}
      <View style={[styles.line, styles.sideline, { left: `${SIDELINE_INSET * 100}%` }]} />
      <View style={[styles.line, styles.sideline, { right: `${SIDELINE_INSET * 100}%` }]} />
      {yardCount > 1
        ? Array.from({ length: hashCount }, (_, i) => (
            <View
              key={`hash-${i}`}
              style={[styles.line, styles.hash, { top: hashRow, left: hashStart + i * HASH_GAP }]}
            />
          ))
        : null}
    </View>
  );
}

const styles = StyleSheet.create({
  line: { position: "absolute", backgroundColor: colors.fieldLine },
  yard: { left: 0, right: 0, height: StyleSheet.hairlineWidth * 2 },
  sideline: { top: 0, bottom: 0, width: StyleSheet.hairlineWidth * 2 },
  hash: { width: HASH_WIDTH, height: StyleSheet.hairlineWidth * 2 },
});
