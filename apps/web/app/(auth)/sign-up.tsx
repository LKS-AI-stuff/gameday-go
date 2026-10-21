import { SignUpScreen } from "@gamedaygo/ui";
import { router } from "expo-router";

export default function SignUpRoute() {
  return (
    <SignUpScreen
      onSignIn={() => router.replace("/sign-in")}
      onCreated={(email) => router.replace({ pathname: "/verify-email", params: { email } })}
    />
  );
}
