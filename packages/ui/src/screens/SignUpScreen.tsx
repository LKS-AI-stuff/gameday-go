import { signUpSchema, type SignUpValues } from "@gamedaygo/shared";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { StyleSheet, View } from "react-native";
import { Button, Checkbox, HelperText, Snackbar } from "react-native-paper";

import { useAuth } from "../auth/AuthProvider";
import { AUTH_MESSAGES } from "../auth/messages";
import { HeroTitle, NotAffiliatedNote, Wordmark } from "../components/Brand";
import { FormTextField } from "../components/FormTextField";
import { Panel } from "../components/Panel";
import { Screen } from "../components/Screen";
import { spacing } from "../theme/tokens";

interface SignUpScreenProps {
  onSignIn: () => void;
  /** Account created; the user now verifies their email. */
  onCreated: (email: string) => void;
}

/** UI/UX §7.1: email, password, confirm password and the required 18+ checkbox (FR-A3). */
export function SignUpScreen({ onSignIn, onCreated }: SignUpScreenProps) {
  const { signUp } = useAuth();
  const [snackbar, setSnackbar] = useState<string | null>(null);
  const { control, handleSubmit, setError, formState } = useForm<SignUpValues>({
    resolver: zodResolver(signUpSchema),
    defaultValues: { email: "", password: "", confirmPassword: "", ageConfirmed: false },
  });
  const busy = formState.isSubmitting;

  const submitForm = handleSubmit(async ({ email, password }) => {
    const result = await signUp(email, password);
    if (result.ok) onCreated(email);
    else if (result.error === "weak_password")
      setError("password", { message: AUTH_MESSAGES.weak_password });
    else setSnackbar(AUTH_MESSAGES[result.error]);
  });
  const onSubmit = () => void submitForm();

  return (
    <Screen
      variant="form"
      hero={
        <>
          <Wordmark size="compact" />
          <HeroTitle>Create your account</HeroTitle>
        </>
      }
    >
      <Panel variant="glass" style={styles.form}>
        <FormTextField
          control={control}
          name="email"
          label="Email"
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          textContentType="emailAddress"
          disabled={busy}
        />
        <FormTextField
          control={control}
          name="password"
          label="Password"
          secureTextEntry
          autoComplete="new-password"
          textContentType="newPassword"
          disabled={busy}
        />
        <FormTextField
          control={control}
          name="confirmPassword"
          label="Confirm password"
          secureTextEntry
          autoComplete="new-password"
          textContentType="newPassword"
          disabled={busy}
        />
        <Controller
          control={control}
          name="ageConfirmed"
          render={({ field: { value, onChange }, fieldState: { error } }) => (
            <View>
              <Checkbox.Item
                label="I'm 18 or older"
                status={value ? "checked" : "unchecked"}
                onPress={() => onChange(!value)}
                disabled={busy}
                position="leading"
                mode="android"
                accessibilityLabel="I'm 18 or older"
              />
              <HelperText type="error" visible={!!error}>
                {error?.message}
              </HelperText>
            </View>
          )}
        />
        <Button mode="contained" onPress={onSubmit} loading={busy} disabled={busy}>
          Create account
        </Button>
        <Button mode="text" onPress={onSignIn} disabled={busy}>
          Already have an account? Sign in
        </Button>
        <NotAffiliatedNote />
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
