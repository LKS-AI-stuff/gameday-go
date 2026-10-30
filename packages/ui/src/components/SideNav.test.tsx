import { fireEvent, render, screen } from "@testing-library/react-native";

import { TABS } from "../navigation";
import { SideNav } from "./SideNav";

async function renderNav(current: string | null = "home") {
  const onNavigate = jest.fn();
  await render(<SideNav items={TABS} current={current} onNavigate={onNavigate} />);
  return onNavigate;
}

describe("Side navigation on wide web (UI/UX §2.2)", () => {
  it("is open when the app loads, with the current page selected", async () => {
    await renderNav();
    expect(screen.getByRole("link", { name: "Home", selected: true })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Schedule", selected: false })).toBeTruthy();
  });

  it("selects nothing on pages outside the four destinations", async () => {
    await renderNav(null);
    for (const tab of TABS) {
      expect(screen.getByRole("link", { name: tab.title, selected: false })).toBeTruthy();
    }
  });

  it("goes to the chosen page and stays open", async () => {
    const onNavigate = await renderNav();
    await fireEvent.press(screen.getByRole("link", { name: "Schedule" }));
    expect(onNavigate).toHaveBeenCalledWith("schedule");
    expect(screen.getByRole("link", { name: "Schedule" })).toBeTruthy();
  });

  it("slides shut from its edge tab and back open", async () => {
    await renderNav();
    await fireEvent.press(screen.getByRole("button", { name: "Hide menu" }));
    expect(screen.queryByRole("link", { name: "Home" })).toBeNull();
    await fireEvent.press(screen.getByRole("button", { name: "Show menu" }));
    expect(screen.getByRole("link", { name: "Home" })).toBeTruthy();
  });
});
