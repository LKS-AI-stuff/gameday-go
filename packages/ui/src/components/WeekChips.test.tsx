import { fireEvent, render, screen } from "@testing-library/react-native";
import { PaperProvider } from "react-native-paper";

import { paperTheme } from "../theme/paperTheme";
import { WeekChips } from "./WeekChips";

const WEEKS = Array.from({ length: 18 }, (_, i) => ({ week: i + 1, label: `WEEK ${i + 1}` }));
const titleCase = (label: string) => label.charAt(0) + label.slice(1).toLowerCase();

describe("WeekChips (UI/UX §7.4)", () => {
  it("selects a week; phones swipe, so there are no arrow buttons", async () => {
    const onSelect = jest.fn();
    await render(
      <PaperProvider theme={paperTheme}>
        <WeekChips weeks={WEEKS} selected={11} onSelect={onSelect} chipLabel={titleCase} />
      </PaperProvider>,
    );
    expect(screen.getByText("WK 11")).toBeTruthy();
    await fireEvent.press(screen.getByLabelText("Week 1"));
    expect(onSelect).toHaveBeenCalledWith(1);
    expect(screen.queryByLabelText("Earlier weeks")).toBeNull();
    expect(screen.queryByLabelText("Later weeks")).toBeNull();
  });
});
