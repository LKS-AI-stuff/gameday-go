// Public client settings (TDD §13). Expo inlines EXPO_PUBLIC_* at build time, so each
// variable must be read with a literal `process.env.NAME`. Never put secrets here (NFR-12).

function required(name: string, value: string | undefined): string {
  if (!value)
    throw new Error(`${name} is not set. Copy apps/mobile/.env.example to apps/mobile/.env.`);
  return value;
}

export const env = {
  apiUrl: required("EXPO_PUBLIC_API_URL", process.env.EXPO_PUBLIC_API_URL),
  supabaseUrl: required("EXPO_PUBLIC_SUPABASE_URL", process.env.EXPO_PUBLIC_SUPABASE_URL),
  supabaseAnonKey: required(
    "EXPO_PUBLIC_SUPABASE_ANON_KEY",
    process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY,
  ),
};
