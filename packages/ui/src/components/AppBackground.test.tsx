import { act, render, screen } from "@testing-library/react-native";
import { Dimensions } from "react-native";

import { AppBackground } from "./AppBackground";

function setWindow(width: number, height: number) {
  const size = { width, height, scale: 2, fontScale: 1 };
  Dimensions.set({ window: size, screen: size });
}

it("uses the tall image on phones and narrow windows", async () => {
  setWindow(390, 844);
  await render(<AppBackground>{null}</AppBackground>);
  expect(screen.getByTestId("app-background")).toBeTruthy();
});

it("uses the wide image on landscape screens", async () => {
  setWindow(1440, 900);
  await render(<AppBackground>{null}</AppBackground>);
  expect(screen.getByTestId("app-background-wide")).toBeTruthy();
});

it("switches when the window is resized", async () => {
  setWindow(390, 844);
  await render(<AppBackground>{null}</AppBackground>);
  await act(async () => setWindow(1280, 800));
  expect(screen.getByTestId("app-background-wide")).toBeTruthy();
});
