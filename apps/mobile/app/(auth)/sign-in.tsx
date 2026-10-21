import { SignInScreen } from "@gamedaygo/ui";
import { router } from "expo-router";

export default function SignInRoute() {
  return (
    <SignInScreen
      onCreateAccount={() => router.push("/sign-up")}
      onUnverified={(email) => router.push({ pathname: "/verify-email", params: { email } })}
    />
  );
}
