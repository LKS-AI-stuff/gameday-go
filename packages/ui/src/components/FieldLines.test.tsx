import { act, fireEvent, render, screen } from "@testing-library/react-native";

import { FieldLines } from "./FieldLines";

describe("FieldLines", () => {
  it("is decorative: hidden from screen readers and touches", async () => {
    await render(<FieldLines />);
    const pattern = screen.getByTestId("field-lines", { includeHiddenElements: true });
    expect(pattern.props.importantForAccessibility).toBe("no-hide-descendants");
    expect(pattern.props.accessibilityElementsHidden).toBe(true);
    expect(pattern.props.pointerEvents).toBe("none");
  });

  it("draws yard lines, sidelines and hash marks once it knows its size", async () => {
    await render(<FieldLines />);
    const pattern = screen.getByTestId("field-lines", { includeHiddenElements: true });
    expect(pattern.children).toHaveLength(2); // only the two sidelines before layout

    await act(async () => {
      await fireEvent(pattern, "layout", { nativeEvent: { layout: { width: 390, height: 320 } } });
    });

    // 320 / 40 = 8 yard lines + 2 sidelines + a row of hash marks
    expect(pattern.children.length).toBeGreaterThan(10);
  });
});
