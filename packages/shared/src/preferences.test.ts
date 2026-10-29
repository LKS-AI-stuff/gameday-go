import { maxTicketPriceSchema, preferencesSchema } from "./preferences";
import { tagExplanation, tagLabel } from "./tags";

const valid = {
  favorite_team_ids: ["CHI"],
  home_zip: "60601",
  travel: "medium",
  spending: "less",
  max_ticket_price_usd: 90,
  viewing: "bar",
  notification_level: "medium",
  timezone: "America/Chicago",
};

describe("preferencesSchema", () => {
  it("accepts the six preferences", () => {
    expect(preferencesSchema.safeParse(valid).success).toBe(true);
  });

  it("needs at least one team and a 5-digit ZIP (AC-2, FR-P3)", () => {
    expect(preferencesSchema.safeParse({ ...valid, favorite_team_ids: [] }).success).toBe(false);
    expect(preferencesSchema.safeParse({ ...valid, home_zip: "6060" }).success).toBe(false);
  });
});

describe("maxTicketPriceSchema", () => {
  it("is optional and whole dollars", () => {
    expect(maxTicketPriceSchema.parse("")).toBeNull();
    expect(maxTicketPriceSchema.parse(" 90 ")).toBe(90);
    expect(maxTicketPriceSchema.safeParse("12.5").success).toBe(false);
    expect(maxTicketPriceSchema.safeParse("0").success).toBe(false);
    expect(maxTicketPriceSchema.safeParse("5001").success).toBe(false);
  });
});

describe("tags", () => {
  it("labels and explains tags", () => {
    expect(tagLabel("division_rivalry")).toBe("DIVISION RIVALRY");
    expect(tagExplanation("featured_rivalry", "Recent Super Bowl opponents")).toBe(
      "A well-known rivalry: Recent Super Bowl opponents.",
    );
    expect(tagLabel("unknown_tag")).toBe("UNKNOWN TAG");
  });
});
