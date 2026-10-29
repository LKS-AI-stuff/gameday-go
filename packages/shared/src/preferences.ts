import { z } from "zod";

// Onboarding preferences P1–P6 (BRD §7.1, UI/UX §7.2). The server validates the same rules.

export type Travel = "low" | "medium" | "high";
export type Spending = "less" | "medium" | "more";
export type Viewing = "stadium" | "bar" | "home" | "flexible";
export type NotificationLevel = "off" | "low" | "medium" | "high";

export interface Option<T extends string> {
  value: T;
  label: string;
  helper: string;
}

export const TRAVEL_OPTIONS: Option<Travel>[] = [
  { value: "low", label: "Low", helper: "Local games only (within 75 mi)." },
  {
    value: "medium",
    label: "Medium",
    helper: "We'll suggest trips for big games, like playoffs and rivalries.",
  },
  { value: "high", label: "High", helper: "Road trips for any game that fits." },
];

export const SPENDING_OPTIONS: Option<Spending>[] = [
  { value: "less", label: "Less", helper: "Cheapest options first, like a bar or home." },
  { value: "medium", label: "Medium", helper: "A balance of price and experience." },
  { value: "more", label: "More", helper: "Better experiences, within your max." },
];

export const VIEWING_OPTIONS: Option<Viewing>[] = [
  { value: "stadium", label: "Stadium", helper: "Tickets first, if travel allows." },
  { value: "bar", label: "Sports bar", helper: "Nearby bars first." },
  { value: "home", label: "Home", helper: "Kickoff details and a reminder." },
  { value: "flexible", label: "Flexible", helper: "Compare everything and show trade-offs." },
];

export const NOTIFICATION_OPTIONS: Option<NotificationLevel>[] = [
  { value: "off", label: "Off", helper: "No emails or reminders. Alerts stay in your inbox." },
  {
    value: "low",
    label: "Low",
    helper: "Alerts you set up and schedule changes for your games.",
  },
  {
    value: "medium",
    label: "Medium",
    helper: "Alerts you set up, schedule changes and game-day reminders.",
  },
  { value: "high", label: "High", helper: "Everything in Medium, plus a weekly digest." },
];

export const PREFERENCE_DEFAULTS = {
  travel: "medium" as Travel,
  spending: "medium" as Spending,
  viewing: "flexible" as Viewing,
  notificationLevel: "medium" as NotificationLevel,
};

export const MAX_TICKET_PRICE_USD = 5000;

export const zipSchema = z.string().regex(/^\d{5}$/, { error: "Enter a 5-digit ZIP" });

export const maxTicketPriceSchema = z
  .string()
  .trim()
  .transform((v, ctx) => {
    if (v === "") return null;
    const n = Number(v);
    if (!Number.isInteger(n) || n < 1 || n > MAX_TICKET_PRICE_USD) {
      ctx.addIssue({
        code: "custom",
        message: `Enter whole dollars from 1 to ${MAX_TICKET_PRICE_USD}`,
      });
      return z.NEVER;
    }
    return n;
  });

export const preferencesSchema = z.object({
  favorite_team_ids: z.array(z.string()).min(1, { error: "Pick at least one team" }),
  home_zip: zipSchema,
  travel: z.enum(["low", "medium", "high"]),
  spending: z.enum(["less", "medium", "more"]),
  max_ticket_price_usd: z.number().int().min(1).max(MAX_TICKET_PRICE_USD).nullable(),
  viewing: z.enum(["stadium", "bar", "home", "flexible"]),
  notification_level: z.enum(["off", "low", "medium", "high"]),
  timezone: z.string().min(1),
});
export type PreferencesValues = z.infer<typeof preferencesSchema>;

/** Which email categories each level includes (BR-N1–N4); others show as off in Settings. */
export const CATEGORIES_BY_LEVEL: Record<NotificationLevel, string[]> = {
  off: [],
  low: ["watch_hit", "schedule_change"],
  medium: ["watch_hit", "schedule_change", "reminder"],
  high: ["watch_hit", "schedule_change", "reminder", "digest"],
};

/** US time zones for the Settings picker (A2: US users). */
export const US_TIME_ZONES: { value: string; label: string }[] = [
  { value: "America/New_York", label: "Eastern (New York)" },
  { value: "America/Chicago", label: "Central (Chicago)" },
  { value: "America/Denver", label: "Mountain (Denver)" },
  { value: "America/Phoenix", label: "Arizona (Phoenix)" },
  { value: "America/Los_Angeles", label: "Pacific (Los Angeles)" },
  { value: "America/Anchorage", label: "Alaska (Anchorage)" },
  { value: "Pacific/Honolulu", label: "Hawaii (Honolulu)" },
];
