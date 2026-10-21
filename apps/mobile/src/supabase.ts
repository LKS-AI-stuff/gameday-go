import { createClient } from "@supabase/supabase-js";
import { AppState } from "react-native";

import { env } from "./env";
import { secureStorage } from "./secureStorage";

// Supabase is used for sign-in only; app data goes through the backend (TDD §2.1).
export const supabase = createClient(env.supabaseUrl, env.supabaseAnonKey, {
  auth: {
    storage: secureStorage,
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false,
  },
});

// Refresh tokens only while the app is in the foreground.
AppState.addEventListener("change", (state) => {
  if (state === "active") supabase.auth.startAutoRefresh();
  else supabase.auth.stopAutoRefresh();
});
