import { useEffect, useState } from "react";
import { StyleSheet, Text } from "react-native";
import { Button, Snackbar } from "react-native-paper";

import { useAuth } from "../auth/AuthProvider";
import { AUTH_MESSAGES } from "../auth/messages";
import { HeroTitle, Wordmark } from "../components/Brand";
import { Panel } from "../components/Panel";
import { Screen } from "../components/Screen";
import { colors, spacing, type } from "../theme/tokens";

export const RESEND_COOLDOWN_S = 60;

interface VerifyEmailScreenProps {
  email: string;
  onUseDifferentEmail: () => void;
  onSignIn: () => void;
}

/** UI/UX §7.1 verify email screen, with a 60-second resend cooldown. */
export function VerifyEmailScreen({
  email,
  onUseDifferentEmail,
  onSignIn,
}: VerifyEmailScreenProps) {
  const { resendVerification } = useAuth();
  const [cooldown, setCooldown] = useState(RESEND_COOLDOWN_S);
  const [sending, setSending] = useState(false);
  const [snackbar, setSnackbar] = useState<string | null>(null);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setTimeout(() => setCooldown((s) => s - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  const resend = async () => {
    setSending(true);
    const result = await resendVerification(email);
    setSending(false);
    setSnackbar(result.ok ? "Verification email sent" : AUTH_MESSAGES[result.error]);
    if (result.ok) setCooldown(RESEND_COOLDOWN_S);
  };

  return (
    <Screen
      variant="form"
      hero={
        <>
          <Wordmark size="compact" />
          <HeroTitle>Check your inbox</HeroTitle>
        </>
      }
    >
      <Panel variant="glass" style={styles.form}>
        <Text style={[type.body, { color: colors.text }]}>
          We sent a link to <Text style={{ fontWeight: "600" }}>{email}</Text>. Open it to verify
          your account, then sign in.
        </Text>
        <Button mode="contained" onPress={onSignIn}>
          {"I've verified, sign in"}
        </Button>
        <Button
          mode="outlined"
          onPress={resend}
          loading={sending}
          disabled={sending || cooldown > 0}
        >
          {cooldown > 0 ? `Resend email (${cooldown}s)` : "Resend email"}
        </Button>
        <Button mode="text" onPress={onUseDifferentEmail}>
          Use a different email
        </Button>
      </Panel>
      <Snackbar visible={snackbar !== null} onDismiss={() => setSnackbar(null)} duration={4000}>
        {snackbar ?? ""}
      </Snackbar>
    </Screen>
  );
}

const styles = StyleSheet.create({
  form: { gap: spacing.md, padding: spacing.xl },
});
