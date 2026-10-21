import { createClient } from "@supabase/supabase-js";

import { env } from "./env";

// Supabase is used for sign-in only; app data goes through the backend (TDD §2.1).
// Sessions persist in localStorage (TDD §4.1). The email verification link lands here
// with the session in the URL, which signs the user in.
export const supabase = createClient(env.supabaseUrl, env.supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
  },
});
