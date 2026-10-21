import { fireEvent, screen, waitFor } from "@testing-library/react-native";

import { fakeSupabase, renderWithProviders } from "../test-utils";
import { SignInScreen } from "./SignInScreen";
import { SignUpScreen } from "./SignUpScreen";

async function fill(label: string, text: string) {
  await fireEvent.changeText(screen.getByLabelText(label), text);
}

describe("SignUpScreen", () => {
  it("requires the 18+ confirmation before creating an account (FR-A3)", async () => {
    const { client, auth } = fakeSupabase();
    const onCreated = jest.fn();
    await renderWithProviders(<SignUpScreen onSignIn={jest.fn()} onCreated={onCreated} />, client);

    await fill("Email", "ben@example.com");
    await fill("Password", "bears2026");
    await fill("Confirm password", "bears2026");
    await fireEvent.press(screen.getByText("Create account"));

    expect(await screen.findByText("You must be 18 or older to use GameDay Go")).toBeTruthy();
    expect(auth.signUp).not.toHaveBeenCalled();
    expect(onCreated).not.toHaveBeenCalled();
  });

  it("creates the account with the age confirmation in user metadata", async () => {
    const { client, auth } = fakeSupabase();
    const onCreated = jest.fn();
    await renderWithProviders(<SignUpScreen onSignIn={jest.fn()} onCreated={onCreated} />, client);

    await fill("Email", " ben@example.com ");
    await fill("Password", "bears2026");
    await fill("Confirm password", "bears2026");
    await fireEvent.press(screen.getByLabelText("I'm 18 or older"));
    await fireEvent.press(screen.getByText("Create account"));

    await waitFor(() => expect(onCreated).toHaveBeenCalledWith("ben@example.com"));
    expect(auth.signUp).toHaveBeenCalledWith({
      email: "ben@example.com",
      password: "bears2026",
      options: { data: { age_confirmed: true }, emailRedirectTo: undefined },
    });
  });

  it("shows field errors for an invalid form", async () => {
    const { client } = fakeSupabase();
    await renderWithProviders(<SignUpScreen onSignIn={jest.fn()} onCreated={jest.fn()} />, client);

    await fill("Email", "nope");
    await fill("Password", "short");
    await fill("Confirm password", "other");
    await fireEvent.press(screen.getByText("Create account"));

    expect(await screen.findByText("Enter a valid email address")).toBeTruthy();
    expect(screen.getByText("Use at least 8 characters")).toBeTruthy();
    expect(screen.getByText("Passwords don't match")).toBeTruthy();
  });
});

describe("SignInScreen", () => {
  it("shows an inline error for wrong credentials", async () => {
    const { client } = fakeSupabase({
      signInWithPassword: jest.fn().mockResolvedValue({ error: { code: "invalid_credentials" } }),
    });
    await renderWithProviders(
      <SignInScreen onCreateAccount={jest.fn()} onUnverified={jest.fn()} />,
      client,
    );

    await fill("Email", "ben@example.com");
    await fill("Password", "wrong-pass1");
    await fireEvent.press(screen.getByText("Sign in"));

    expect(await screen.findByText("Incorrect email or password")).toBeTruthy();
  });

  it("sends unverified users to the verify email screen (FR-O11)", async () => {
    const onUnverified = jest.fn();
    const { client } = fakeSupabase({
      signInWithPassword: jest.fn().mockResolvedValue({ error: { code: "email_not_confirmed" } }),
    });
    await renderWithProviders(
      <SignInScreen onCreateAccount={jest.fn()} onUnverified={onUnverified} />,
      client,
    );

    await fill("Email", "ben@example.com");
    await fill("Password", "bears2026");
    await fireEvent.press(screen.getByText("Sign in"));

    await waitFor(() => expect(onUnverified).toHaveBeenCalledWith("ben@example.com"));
  });
});
