import { useMe } from "@gamedaygo/api-client";
import { deviceTimeZone } from "@gamedaygo/shared";

import { useAuth } from "../auth/AuthProvider";

/** The signed-in user's ID and display time zone (stored zone, else the device's; NFR-4). */
export function useViewer() {
  const { userId } = useAuth();
  const me = useMe(userId);
  return { userId, me, timeZone: me.data?.timezone ?? deviceTimeZone() };
}
