import { VerifyEmailScreen } from "@gamedaygo/ui";
import { router, useLocalSearchParams } from "expo-router";

export default function VerifyEmailRoute() {
  const { email } = useLocalSearchParams<{ email?: string }>();
  return (
    <VerifyEmailScreen
      email={email ?? ""}
      onUseDifferentEmail={() => router.replace("/sign-up")}
      onSignIn={() => router.replace("/sign-in")}
    />
  );
}
