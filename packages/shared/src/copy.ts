// Product strings used across screens (UI/UX §5.2, §8.2).
export const APP_NAME = "GameDay Go";
export const TAGLINE = "Your NFL game day, planned.";
export const NOT_AFFILIATED = "GameDay Go is not affiliated with the NFL or any team.";

// UI/UX §8.2 standard strings used from M1.
export const COPY = {
  genericError: "Something went wrong. Try again.",
  offline: "You're offline. Showing saved data.",
  scheduleNotOut: "Next season's schedule isn't out yet.",
  scheduleNotOutDetail: "We'll be ready to plan as soon as it's released.",
  noMoreGames: "No more games for your teams this season.",
  zipNotFound: "We couldn't find that ZIP. Check the 5 digits.",
  locationDenied: "No problem, enter your ZIP instead.",
  preferenceChangeNote: "Changes apply to new plans. Saved plans stay as they are.",
  planningSoon: "Planning arrives soon",
  outsideTravelArea: (level: string) => `Outside your travel area (${level})`,
  maxPriceNote: "Your max is a hard limit. We never show tickets above it.",
  scheduleSource: "API-Sports",
} as const;
