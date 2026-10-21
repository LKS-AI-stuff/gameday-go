import { useAuth } from "@gamedaygo/ui";
import { Redirect } from "expo-router";

// "/" sends each user to the right place; the auth guard in _layout does the rest.
export default function IndexRoute() {
  const { status } = useAuth();
  return <Redirect href={status === "signedIn" ? "/home" : "/sign-in"} />;
}
