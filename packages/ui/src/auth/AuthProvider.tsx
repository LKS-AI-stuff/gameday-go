import type { Session, SupabaseClient } from "@supabase/supabase-js";
import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type AuthStatus = "loading" | "signedOut" | "signedIn";

/** Supabase error codes the screens show specific copy for; everything else is "unknown". */
export type AuthErrorCode =
  | "invalid_credentials"
  | "email_not_confirmed"
  | "over_email_send_rate_limit"
  | "weak_password"
  | "network"
  | "unknown";

export type AuthResult = { ok: true } | { ok: false; error: AuthErrorCode };

interface AuthContextValue {
  status: AuthStatus;
  session: Session | null;
  userId: string | null;
  email: string | null;
  signIn: (email: string, password: string) => Promise<AuthResult>;
  /** Creates the account; the user must verify their email before signing in (FR-O11). */
  signUp: (email: string, password: string) => Promise<AuthResult>;
  resendVerification: (email: string) => Promise<AuthResult>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const KNOWN_CODES = new Set<AuthErrorCode>([
  "invalid_credentials",
  "email_not_confirmed",
  "over_email_send_rate_limit",
  "weak_password",
]);

function toResult(error: { code?: string; name?: string } | null): AuthResult {
  if (!error) return { ok: true };
  if (error.name === "AuthRetryableFetchError") return { ok: false, error: "network" };
  const code = error.code as AuthErrorCode | undefined;
  return { ok: false, error: code && KNOWN_CODES.has(code) ? code : "unknown" };
}

interface AuthProviderProps {
  supabase: SupabaseClient;
  /** Where the email verification link lands (the web app). Undefined uses Supabase's site URL. */
  emailRedirectTo?: string;
  children: ReactNode;
}

export function AuthProvider({ supabase, emailRedirectTo, children }: AuthProviderProps) {
  const queryClient = useQueryClient();
  const [session, setSession] = useState<Session | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  useEffect(() => {
    let mounted = true;
    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      setSession(data.session);
      setStatus(data.session ? "signedIn" : "signedOut");
    });
    const { data } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
      setStatus(next ? "signedIn" : "signedOut");
    });
    return () => {
      mounted = false;
      data.subscription.unsubscribe();
    };
  }, [supabase]);

  const signIn = useCallback(
    async (email: string, password: string) =>
      toResult((await supabase.auth.signInWithPassword({ email, password })).error),
    [supabase],
  );

  const signUp = useCallback(
    async (email: string, password: string) => {
      const { error } = await supabase.auth.signUp({
        email,
        password,
        // The sign-up form's 18+ checkbox; the backend copies it on first request (TDD §6).
        options: { data: { age_confirmed: true }, emailRedirectTo },
      });
      return toResult(error);
    },
    [supabase, emailRedirectTo],
  );

  const resendVerification = useCallback(
    async (email: string) =>
      toResult(
        (await supabase.auth.resend({ type: "signup", email, options: { emailRedirectTo } })).error,
      ),
    [supabase, emailRedirectTo],
  );

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    // Never show one user's cached data to the next (FR-A5).
    queryClient.clear();
  }, [supabase, queryClient]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      session,
      userId: session?.user.id ?? null,
      email: session?.user.email ?? null,
      signIn,
      signUp,
      resendVerification,
      signOut,
    }),
    [status, session, signIn, signUp, resendVerification, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
