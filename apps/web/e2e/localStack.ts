// Test accounts are created and removed through the local Supabase Auth Admin API. The
// server-only secret key comes from the git-ignored repo .env via the `e2e` script, never from
// an EXPO_PUBLIC_ variable.
const SUPABASE_URL = process.env.E2E_SUPABASE_URL ?? "http://127.0.0.1:54321";

function secretKey(): string {
  const key = process.env.E2E_SUPABASE_SECRET_KEY;
  if (!key) throw new Error("Run `pnpm e2e`: it reads SUPABASE_SECRET_KEY from the repo .env");
  return key;
}

export const PASSWORD = "E2e-onboard-2026";

/** A verified account that confirmed 18+ at sign-up, ready to sign in. */
export async function createVerifiedUser(email: string): Promise<string> {
  const response = await fetch(`${SUPABASE_URL}/auth/v1/admin/users`, {
    method: "POST",
    headers: { apikey: secretKey(), "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      password: PASSWORD,
      email_confirm: true,
      user_metadata: { age_confirmed: true },
    }),
  });
  if (!response.ok) throw new Error(`creating the test user failed: ${response.status}`);
  const user = (await response.json()) as { id: string };
  return user.id;
}

export async function deleteUser(id: string): Promise<void> {
  await fetch(`${SUPABASE_URL}/auth/v1/admin/users/${id}`, {
    method: "DELETE",
    headers: { apikey: secretKey() },
  });
}
