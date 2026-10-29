import { expect, test } from "@playwright/test";

import { createVerifiedUser, deleteUser, PASSWORD } from "./localStack";

// J1 and J2 on web: onboard with the six preferences, browse the schedule and open a game
// (the M1 slice of AC-28), then delete the account from Settings (FR-A4), which cleans up.
test("onboard, see your next games, browse the schedule and open a game", async ({
  page,
}, testInfo) => {
  const email = `e2e-${testInfo.project.name}-${Date.now()}@example.com`;
  const userId = await createVerifiedUser(email);
  // React errors open Expo's dev overlay; fail on them rather than on a blocked tap.
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    // Network failures are logged as "Failed to load resource" (e.g. Auth's 403 on logout
    // once the account is deleted); those aren't app errors.
    if (message.type() === "error" && !message.text().startsWith("Failed to load resource")) {
      errors.push(message.text());
    }
  });
  try {
    await page.goto("/");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();

    // Onboarding: six questions, then review (UI/UX §7.2).
    await expect(page.getByText("Who do you root for?")).toBeVisible();
    await expect(page.getByText("Step 1 of 6")).toBeVisible();
    await page.getByLabel("Chicago Bears").click();
    await page.getByRole("button", { name: "Next" }).click();
    await page.getByLabel("ZIP code").fill("60601");
    await expect(page.getByText("Chicago, IL")).toBeVisible();
    for (let step = 3; step <= 6; step++) {
      await page.getByRole("button", { name: "Next" }).click();
      await expect(page.getByText(`Step ${step} of 6`)).toBeVisible();
    }
    await page.getByRole("button", { name: "Next" }).click();
    await expect(page.getByText("Review", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Start planning" }).click();

    // Home: the next Bears game (FR-SC1), with kickoff in a named time zone (NFR-4).
    await expect(page.getByText("YOUR NEXT GAMES")).toBeVisible();
    const card = page.getByRole("button", { name: /Bears/ }).first();
    await expect(card).toBeVisible();
    await expect(card).toContainText(/ (CT|ET|PT|MT|MST|AKT|HT|HST|GMT[+-]?\d*|UTC)/);

    // Schedule: week chips and day groups (FR-SC2), then a game's detail (FR-SC3, FR-SC4).
    await page.getByRole("tab", { name: /Schedule/i }).click();
    await expect(page.getByText("SCHEDULE", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: / at / }).first().click();
    await expect(page.getByText("ABOUT THIS GAME")).toBeVisible();
    await expect(page.getByText(/API-Sports · schedule updated/)).toBeVisible();

    // Settings: delete the account, which needs DELETE typed (UI/UX §5.4).
    await page.getByLabel("Back").filter({ visible: true }).click();
    await expect(page.getByText("SCHEDULE", { exact: true })).toBeVisible();
    // Inactive tabs stay mounted with their own app bar, so open Settings by URL.
    await page.goto("/settings");
    await page.getByRole("button", { name: "Delete account" }).click();
    await page.getByLabel("Type DELETE to confirm").fill("DELETE");
    await page.getByRole("button", { name: "Delete account" }).last().click();
    await expect(page.getByText("New here? Create account")).toBeVisible();
    expect(errors).toEqual([]);
  } finally {
    await deleteUser(userId);
  }
});
