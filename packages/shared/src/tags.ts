// Significance tags (BRD §7.6, UI/UX §6.4): labels and one-sentence explanations.

export type TagWeight = "high" | "medium" | "info";

export interface TagInfo {
  label: string;
  explanation: string;
}

export const TAGS: Record<string, TagInfo> = {
  playoff: { label: "Playoff game", explanation: "A playoff game: win or go home." },
  division_rivalry: {
    label: "Division rivalry",
    explanation: "Both teams play in the same division and meet twice every season.",
  },
  featured_rivalry: { label: "Featured rivalry", explanation: "A well-known rivalry." },
  primetime: {
    label: "Primetime",
    explanation: "A Thursday, Sunday or Monday night kickoff.",
  },
  home_opener: {
    label: "Home opener",
    explanation: "The home team's first home game this season.",
  },
  home_finale: { label: "Home finale", explanation: "The home team's last home game this season." },
  international: {
    label: "International game",
    explanation: "Played outside the US. Shown in the schedule, never suggested as a trip.",
  },
};

export function tagLabel(tag: string): string {
  return (TAGS[tag]?.label ?? tag.replace(/_/g, " ")).toUpperCase();
}

/** The featured-rivalry reason comes from the curated list (BRD Appendix B). */
export function tagExplanation(tag: string, detail?: string | null): string {
  if (tag === "featured_rivalry" && detail) return `A well-known rivalry: ${detail}.`;
  return TAGS[tag]?.explanation ?? "";
}
