import type { AuthErrorCode } from "./AuthProvider";

// User-facing copy for auth failures (UI/UX §7.1, §8.2).
export const AUTH_MESSAGES: Record<AuthErrorCode, string> = {
  invalid_credentials: "Incorrect email or password",
  email_not_confirmed: "Verify your email to sign in",
  over_email_send_rate_limit: "Too many emails sent. Try again in a few minutes.",
  weak_password: "Choose a stronger password",
  network: "Can't reach GameDay Go. Check your connection and try again.",
  unknown: "Something went wrong. Try again.",
};
