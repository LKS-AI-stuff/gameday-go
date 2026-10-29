import { useAppEvents, useSavePreferences, useTeams, useZipLookup } from "@gamedaygo/api-client";
import {
  COPY,
  NOTIFICATION_OPTIONS,
  PREFERENCE_DEFAULTS,
  SPENDING_OPTIONS,
  TRAVEL_OPTIONS,
  VIEWING_OPTIONS,
  deviceTimeZone,
  maxTicketPriceSchema,
  type NotificationLevel,
  type Spending,
  type Travel,
  type Viewing,
} from "@gamedaygo/shared";
import { useEffect, useRef, useState } from "react";
import { Platform, StyleSheet, Text, View } from "react-native";
import { Button, Checkbox, HelperText, ProgressBar, Snackbar, TextInput } from "react-native-paper";

import { useAuth } from "../auth/AuthProvider";
import { Wordmark } from "../components/Brand";
import { Panel } from "../components/Panel";
import { PreferenceSelector } from "../components/PreferenceSelector";
import { Screen } from "../components/Screen";
import { ErrorState, Skeleton } from "../components/StateViews";
import { TeamPicker } from "../components/TeamPicker";
import { ZipField } from "../components/ZipField";
import { colors, spacing, type } from "../theme/tokens";

const STEPS = [
  { title: "Who do you root for?", helper: "Pick as many as you like." },
  { title: "Where's home?", helper: "We use this for nearby bars and travel distance." },
  { title: "How far will you go for a game?", helper: "" },
  { title: "How do you like to spend?", helper: "" },
  { title: "How do you like to watch?", helper: "" },
  { title: "How often should we email you?", helper: "" },
] as const;
const REVIEW = STEPS.length;

function platform(): "ios" | "android" | "web" {
  return Platform.OS === "ios" || Platform.OS === "android" ? Platform.OS : "web";
}

function label<T extends string>(options: { value: T; label: string }[], value: T): string {
  return options.find((o) => o.value === value)?.label ?? value;
}

/** Six questions, one per step, then a review (UI/UX §7.2, FR-P1, AC-1). The time zone is
 * taken from the device, not asked (BRD §7.1). */
export function OnboardingScreen() {
  const { userId } = useAuth();
  const teams = useTeams(userId);
  const save = useSavePreferences(userId);
  const sendEvents = useAppEvents();
  const started = useRef(false);

  const [step, setStep] = useState(0);
  const [editing, setEditing] = useState(false);
  const [favorites, setFavorites] = useState<string[]>([]);
  const [zip, setZip] = useState("");
  const [travel, setTravel] = useState<Travel>(PREFERENCE_DEFAULTS.travel);
  const [spending, setSpending] = useState<Spending>(PREFERENCE_DEFAULTS.spending);
  const [withMax, setWithMax] = useState(false);
  const [maxPrice, setMaxPrice] = useState("");
  const [viewing, setViewing] = useState<Viewing>(PREFERENCE_DEFAULTS.viewing);
  const [level, setLevel] = useState<NotificationLevel>(PREFERENCE_DEFAULTS.notificationLevel);
  const [failed, setFailed] = useState(false);
  const zipLookup = useZipLookup(userId, zip);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    sendEvents([
      { name: "onboarding_started", platform: platform(), client_ts: new Date().toISOString() },
    ]);
  }, [sendEvents]);

  const max = maxTicketPriceSchema.safeParse(withMax ? maxPrice : "");
  const canContinue = [favorites.length > 0, zipLookup.isSuccess, true, max.success, true, true][
    step
  ];

  const next = () => setStep(editing ? REVIEW : step + 1);
  const edit = (target: number) => {
    setEditing(true);
    setStep(target);
  };

  const finish = async () => {
    try {
      await save.mutateAsync({
        favorite_team_ids: favorites,
        home_zip: zip,
        travel,
        spending,
        max_ticket_price_usd: max.success ? max.data : null,
        viewing,
        notification_level: level,
        timezone: deviceTimeZone(),
      });
      sendEvents([
        { name: "onboarding_completed", platform: platform(), client_ts: new Date().toISOString() },
      ]);
      // The (app) route guard moves on to Home once `me.onboarded` refreshes.
    } catch {
      setFailed(true);
    }
  };

  const current = step < REVIEW ? STEPS[step] : undefined;
  const teamNames = (teams.data ?? [])
    .filter((t) => favorites.includes(t.id))
    .map((t) => t.nickname)
    .join(", ");
  const summary = [
    teamNames || favorites.join(", "),
    zipLookup.data ? `${zip} · ${zipLookup.data.place_name}, ${zipLookup.data.state}` : zip,
    label(TRAVEL_OPTIONS, travel),
    `${label(SPENDING_OPTIONS, spending)}${max.success && max.data ? ` · max $${max.data}` : ""}`,
    label(VIEWING_OPTIONS, viewing),
    label(NOTIFICATION_OPTIONS, level),
  ];

  return (
    <Screen variant="reading">
      <Wordmark size="compact" />
      <View style={styles.progress}>
        <ProgressBar
          progress={Math.min(step + 1, STEPS.length) / STEPS.length}
          color={colors.primary}
          accessibilityLabel="Onboarding progress"
        />
        <Text style={[type.caption, { color: colors.textMuted }]}>
          {step < REVIEW ? `Step ${step + 1} of ${STEPS.length}` : "Review"}
        </Text>
      </View>

      <Panel variant="glass" style={styles.panel}>
        <Text style={[type.h1, { color: colors.text }]} accessibilityRole="header">
          {current ? current.title : "Ready to plan?"}
        </Text>
        {current?.helper ? (
          <Text style={[type.body, { color: colors.textMuted }]}>{current.helper}</Text>
        ) : null}

        {step === 0 ? (
          teams.isPending ? (
            <Skeleton rows={4} height={56} />
          ) : teams.isError ? (
            <ErrorState error={teams.error} onRetry={() => void teams.refetch()} />
          ) : (
            <TeamPicker teams={teams.data} selected={favorites} onChange={setFavorites} />
          )
        ) : null}
        {step === 1 ? <ZipField userId={userId} value={zip} onChange={setZip} /> : null}
        {step === 2 ? (
          <PreferenceSelector
            label="Travel"
            options={TRAVEL_OPTIONS}
            value={travel}
            onChange={setTravel}
          />
        ) : null}
        {step === 3 ? (
          <View style={styles.stack}>
            <PreferenceSelector
              label="Spending"
              options={SPENDING_OPTIONS}
              value={spending}
              onChange={setSpending}
            />
            <Checkbox.Item
              label="Set a max ticket price"
              status={withMax ? "checked" : "unchecked"}
              onPress={() => setWithMax(!withMax)}
              position="leading"
              labelStyle={[type.body, { color: colors.text, textAlign: "left" }]}
              style={styles.checkbox}
            />
            {withMax ? (
              <View>
                <TextInput
                  mode="outlined"
                  dense
                  value={maxPrice}
                  onChangeText={(t) => setMaxPrice(t.replace(/[^\d]/g, ""))}
                  keyboardType="number-pad"
                  accessibilityLabel="Max ticket price in dollars"
                  left={<TextInput.Affix text="$" />}
                  error={!max.success}
                />
                <HelperText type={max.success ? "info" : "error"} style={styles.helper}>
                  {max.success ? COPY.maxPriceNote : max.error.issues[0]?.message}
                </HelperText>
              </View>
            ) : null}
          </View>
        ) : null}
        {step === 4 ? (
          <PreferenceSelector
            label="Viewing"
            options={VIEWING_OPTIONS}
            value={viewing}
            onChange={setViewing}
            cards
          />
        ) : null}
        {step === 5 ? (
          <PreferenceSelector
            label="Notifications"
            options={NOTIFICATION_OPTIONS}
            value={level}
            onChange={setLevel}
          />
        ) : null}

        {step === REVIEW ? (
          <View style={styles.stack}>
            {STEPS.map((s, i) => (
              <View key={s.title} style={styles.reviewRow}>
                <View style={styles.reviewText}>
                  <Text style={[type.label, { color: colors.textMuted }]}>{s.title}</Text>
                  <Text style={[type.body, { color: colors.text }]}>{summary[i]}</Text>
                </View>
                <Button compact onPress={() => edit(i)} accessibilityLabel={`Edit: ${s.title}`}>
                  Edit
                </Button>
              </View>
            ))}
          </View>
        ) : null}

        <View style={styles.actions}>
          {step > 0 && step < REVIEW && !editing ? (
            <Button mode="text" onPress={() => setStep(step - 1)}>
              Back
            </Button>
          ) : (
            <View />
          )}
          {step < REVIEW ? (
            <Button mode="contained" onPress={next} disabled={!canContinue}>
              {editing ? "Done" : "Next"}
            </Button>
          ) : (
            <Button mode="contained" onPress={() => void finish()} loading={save.isPending}>
              Start planning
            </Button>
          )}
        </View>
      </Panel>
      <Snackbar
        visible={failed}
        onDismiss={() => setFailed(false)}
        action={{ label: "Try again", onPress: () => void finish() }}
      >
        {COPY.genericError}
      </Snackbar>
    </Screen>
  );
}

const styles = StyleSheet.create({
  progress: { gap: spacing.xs },
  panel: { padding: spacing.xl, gap: spacing.lg },
  stack: { gap: spacing.md },
  checkbox: { paddingHorizontal: 0 },
  helper: { paddingHorizontal: 0 },
  reviewRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.outline,
    paddingBottom: spacing.sm,
  },
  reviewText: { flex: 1, gap: spacing.xs },
  actions: { flexDirection: "row", justifyContent: "space-between", marginTop: spacing.sm },
});
