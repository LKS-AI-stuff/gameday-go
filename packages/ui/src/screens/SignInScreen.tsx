import { signInSchema, type SignInValues } from "@gamedaygo/shared";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Button, Snackbar } from "react-native-paper";

import { useAuth } from "../auth/AuthProvider";
import { AUTH_MESSAGES } from "../auth/messages";
import { NotAffiliatedNote, Wordmark } from "../components/Brand";
import { FormTextField } from "../components/FormTextField";
import { Screen } from "../components/Screen";

interface SignInScreenProps {
  onCreateAccount: () => void;
  /** The account exists but its email isn't verified yet (FR-O11). */
  onUnverified: (email: string) => void;
}

/** UI/UX §7.1. Social sign-in is added in M6. */
export function SignInScreen({ onCreateAccount, onUnverified }: SignInScreenProps) {
  const { signIn } = useAuth();
  const [snackbar, setSnackbar] = useState<string | null>(null);
  const { control, handleSubmit, setError, formState } = useForm<SignInValues>({
    resolver: zodResolver(signInSchema),
    defaultValues: { email: "", password: "" },
  });

  const submitForm = handleSubmit(async ({ email, password }) => {
    const result = await signIn(email, password);
    if (result.ok) return; // The router reacts to the new session.
    if (result.error === "email_not_confirmed") onUnverified(email);
    else if (result.error === "invalid_credentials")
      setError("password", { message: AUTH_MESSAGES.invalid_credentials });
    else setSnackbar(AUTH_MESSAGES[result.error]);
  });
  const onSubmit = () => void submitForm();

  return (
    <Screen variant="form">
      <Wordmark />
      <FormTextField
        control={control}
        name="email"
        label="Email"
        autoCapitalize="none"
        autoComplete="email"
        keyboardType="email-address"
        textContentType="emailAddress"
        disabled={formState.isSubmitting}
      />
      <FormTextField
        control={control}
        name="password"
        label="Password"
        secureTextEntry
        autoComplete="current-password"
        textContentType="password"
        disabled={formState.isSubmitting}
        onSubmitEditing={onSubmit}
      />
      <Button
        mode="contained"
        onPress={onSubmit}
        loading={formState.isSubmitting}
        disabled={formState.isSubmitting}
      >
        Sign in
      </Button>
      <Button mode="text" onPress={onCreateAccount} disabled={formState.isSubmitting}>
        New here? Create account
      </Button>
      <NotAffiliatedNote />
      <Snackbar visible={snackbar !== null} onDismiss={() => setSnackbar(null)} duration={4000}>
        {snackbar ?? ""}
      </Snackbar>
    </Screen>
  );
}
