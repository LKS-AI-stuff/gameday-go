import {
  ApiError,
  useDeleteAccount,
  useNotificationSettings,
  usePreferences,
  useSaveNotificationSettings,
  useSavePreferences,
  useTeams,
  useZipLookup,
  type NotificationSettings,
  type Preferences,
} from "@gamedaygo/api-client";
import {
  CATEGORIES_BY_LEVEL,
  COPY,
  NOTIFICATION_OPTIONS,
  SPENDING_OPTIONS,
  TRAVEL_OPTIONS,
  US_TIME_ZONES,
  VIEWING_OPTIONS,
  maxTicketPriceSchema,
  type NotificationLevel,
  type Spending,
  type Travel,
  type Viewing,
} from "@gamedaygo/shared";
import { useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import {
  Button,
  Dialog,
  HelperText,
  IconButton,
  List,
  Portal,
  RadioButton,
  Snackbar,
  Switch,
  TextInput,
} from "react-native-paper";

import { useAuth } from "../auth/AuthProvider";
import { NotAffiliatedNote } from "../components/Brand";
import { Panel, SectionTitle } from "../components/Panel";
import { PreferenceSelector } from "../components/PreferenceSelector";
import { Screen } from "../components/Screen";
import { ErrorState, Skeleton } from "../components/StateViews";
import { TeamPicker } from "../components/TeamPicker";
import { ZipField } from "../components/ZipField";
import { colors, spacing, type } from "../theme/tokens";

type Editing = "teams" | "zip" | "travel" | "spending" | "viewing" | "timezone" | null;

const CATEGORY_LABELS: { key: keyof NotificationSettings["categories"]; label: string }[] = [
  { key: "watch_hit", label: "Alert emails" },
  { key: "schedule_change", label: "Schedule changes" },
  { key: "reminder", label: "Game-day reminders" },
  { key: "digest", label: "Weekly digest" },
];

function optionLabel(options: { value: string; label: string }[], value: string): string {
  return options.find((o) => o.value === value)?.label ?? value;
}

/** UI/UX §7.11 (FR-P2, BR-N9, FR-A4). No theme setting: one dark theme (NFR-5). */
export function SettingsScreen({ onBack, appVersion }: { onBack: () => void; appVersion: string }) {
  const { userId, email, signOut } = useAuth();
  const preferences = usePreferences(userId);
  const notifications = useNotificationSettings(userId);
  const teams = useTeams(userId);
  const savePreferences = useSavePreferences(userId);
  const saveNotifications = useSaveNotificationSettings(userId);
  const [editing, setEditing] = useState<Editing>(null);
  const [deleting, setDeleting] = useState(false);
  const [snackbar, setSnackbar] = useState<string | null>(null);

  if (preferences.isPending || notifications.isPending) {
    return (
      <Screen>
        <Skeleton rows={4} height={64} />
      </Screen>
    );
  }
  if (preferences.isError || notifications.isError) {
    return (
      <Screen>
        <ErrorState
          error={preferences.error ?? notifications.error}
          onRetry={() => {
            void preferences.refetch();
            void notifications.refetch();
          }}
        />
      </Screen>
    );
  }

  const prefs = preferences.data;
  const notify = notifications.data;

  const update = async (change: Partial<Preferences>) => {
    const next = { ...prefs, ...change };
    try {
      await savePreferences.mutateAsync({
        favorite_team_ids: next.favorite_team_ids,
        home_zip: next.home_zip,
        travel: next.travel,
        spending: next.spending,
        max_ticket_price_usd: next.max_ticket_price_usd ?? null,
        viewing: next.viewing,
        notification_level: next.notification_level,
        timezone: next.timezone ?? "America/New_York",
      });
      setEditing(null);
      setSnackbar("Saved");
    } catch {
      setSnackbar(COPY.genericError);
    }
  };

  const updateNotifications = async (next: NotificationSettings) => {
    try {
      await saveNotifications.mutateAsync(next);
    } catch {
      setSnackbar(COPY.genericError);
    }
  };

  const teamNames = (teams.data ?? [])
    .filter((t) => prefs.favorite_team_ids.includes(t.id))
    .map((t) => t.nickname)
    .join(", ");
  const allowed = CATEGORIES_BY_LEVEL[notify.level as NotificationLevel];

  return (
    <Screen>
      <View style={styles.header}>
        <IconButton
          icon="arrow-left"
          iconColor={colors.text}
          onPress={onBack}
          accessibilityLabel="Back"
        />
        <SectionTitle>SETTINGS</SectionTitle>
      </View>

      <Section title="PREFERENCES">
        <Row title="Favorite teams" value={teamNames} onPress={() => setEditing("teams")} />
        <Row
          title="Home ZIP"
          value={
            prefs.home_place
              ? `${prefs.home_zip} · ${prefs.home_place.place_name}, ${prefs.home_place.state}`
              : prefs.home_zip
          }
          onPress={() => setEditing("zip")}
        />
        <Row
          title="Travel"
          value={optionLabel(TRAVEL_OPTIONS, prefs.travel)}
          onPress={() => setEditing("travel")}
        />
        <Row
          title="Spending"
          value={`${optionLabel(SPENDING_OPTIONS, prefs.spending)}${
            prefs.max_ticket_price_usd ? ` · max $${prefs.max_ticket_price_usd}` : ""
          }`}
          onPress={() => setEditing("spending")}
        />
        <Row
          title="Viewing"
          value={optionLabel(VIEWING_OPTIONS, prefs.viewing)}
          onPress={() => setEditing("viewing")}
        />
      </Section>

      <Section title="NOTIFICATIONS">
        <Text style={[type.label, { color: colors.textMuted }]}>Email level</Text>
        <PreferenceSelector
          label="Email level"
          options={NOTIFICATION_OPTIONS}
          value={notify.level as NotificationLevel}
          onChange={(level) => void updateNotifications({ ...notify, level })}
        />
        {CATEGORY_LABELS.map(({ key, label }) => {
          const included = allowed.includes(key);
          return (
            <List.Item
              key={key}
              title={label}
              titleStyle={[type.body, { color: included ? colors.text : colors.textSubtle }]}
              description={included ? undefined : `Not sent at the ${notify.level} level`}
              descriptionStyle={{ color: colors.textSubtle }}
              right={() => (
                <Switch
                  value={included && notify.categories[key]}
                  disabled={!included || saveNotifications.isPending}
                  onValueChange={(on) =>
                    void updateNotifications({
                      ...notify,
                      categories: { ...notify.categories, [key]: on },
                    })
                  }
                  accessibilityLabel={label}
                />
              )}
            />
          );
        })}
        <Row
          title="Time zone"
          value={
            US_TIME_ZONES.find((z) => z.value === prefs.timezone)?.label ?? prefs.timezone ?? ""
          }
          onPress={() => setEditing("timezone")}
        />
      </Section>

      <Section title="ACCOUNT">
        <List.Item
          title="Email"
          description={email ?? ""}
          titleStyle={[type.body, { color: colors.text }]}
          descriptionStyle={{ color: colors.textMuted }}
        />
        <Button mode="outlined" onPress={() => void signOut()}>
          Sign out
        </Button>
        <Button mode="text" textColor={colors.danger} onPress={() => setDeleting(true)}>
          Delete account
        </Button>
      </Section>

      <Section title="ABOUT">
        <Text style={[type.body, { color: colors.textMuted }]}>
          Data sources: schedule from API-Sports. Tickets (Ticketmaster), venues (Google) and your
          planner (OpenAI) arrive in later releases.
        </Text>
        <NotAffiliatedNote />
        <Text style={[type.caption, { color: colors.textSubtle }]}>Version {appVersion}</Text>
      </Section>

      <EditDialog
        editing={editing}
        prefs={prefs}
        userId={userId}
        teams={teams.data ?? []}
        saving={savePreferences.isPending}
        onCancel={() => setEditing(null)}
        onSave={(change) => void update(change)}
      />
      <DeleteAccountDialog
        visible={deleting}
        onDismiss={() => setDeleting(false)}
        onDeleted={() => void signOut()}
      />
      <Snackbar visible={!!snackbar} onDismiss={() => setSnackbar(null)} duration={4000}>
        {snackbar}
      </Snackbar>
    </Screen>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Panel variant="glass" style={styles.section}>
      <Text style={[type.label, { color: colors.textMuted }]} accessibilityRole="header">
        {title}
      </Text>
      {children}
    </Panel>
  );
}

function Row({ title, value, onPress }: { title: string; value: string; onPress: () => void }) {
  return (
    <List.Item
      title={title}
      description={value}
      onPress={onPress}
      titleStyle={[type.body, { color: colors.text }]}
      descriptionStyle={{ color: colors.textMuted }}
      right={(props) => <List.Icon {...props} icon="chevron-right" color={colors.textMuted} />}
      accessibilityLabel={`${title}: ${value}. Edit`}
    />
  );
}

interface EditDialogProps {
  editing: Editing;
  prefs: Preferences;
  userId: string | null;
  teams: Parameters<typeof TeamPicker>[0]["teams"];
  saving: boolean;
  onCancel: () => void;
  onSave: (change: Partial<Preferences>) => void;
}

/** The onboarding control for one preference, with the FR-P4 note. */
function EditDialog({ editing, ...props }: EditDialogProps) {
  return (
    <Portal>
      <Dialog visible={editing !== null} onDismiss={props.onCancel} style={styles.dialog}>
        {editing ? <EditBody key={editing} editing={editing} {...props} /> : null}
      </Dialog>
    </Portal>
  );
}

function EditBody({
  editing,
  prefs,
  userId,
  teams,
  saving,
  onCancel,
  onSave,
}: EditDialogProps & { editing: Exclude<Editing, null> }) {
  const [favorites, setFavorites] = useState(prefs.favorite_team_ids);
  const [zip, setZip] = useState(prefs.home_zip);
  const [travel, setTravel] = useState<Travel>(prefs.travel);
  const [spending, setSpending] = useState<Spending>(prefs.spending);
  const [maxPrice, setMaxPrice] = useState(prefs.max_ticket_price_usd?.toString() ?? "");
  const [viewing, setViewing] = useState<Viewing>(prefs.viewing);
  const [timezone, setTimezone] = useState(prefs.timezone ?? "America/New_York");
  const zipLookup = useZipLookup(userId, zip);
  const max = maxTicketPriceSchema.safeParse(maxPrice);

  const titles: Record<Exclude<Editing, null>, string> = {
    teams: "Favorite teams",
    zip: "Home ZIP",
    travel: "Travel",
    spending: "Spending",
    viewing: "Viewing",
    timezone: "Time zone",
  };
  const valid = {
    teams: favorites.length > 0,
    zip: zipLookup.isSuccess,
    travel: true,
    spending: max.success,
    viewing: true,
    timezone: true,
  }[editing];
  const change: Partial<Preferences> = {
    teams: { favorite_team_ids: favorites },
    zip: { home_zip: zip },
    travel: { travel },
    spending: { spending, max_ticket_price_usd: max.success ? max.data : null },
    viewing: { viewing },
    timezone: { timezone },
  }[editing];
  const zones =
    US_TIME_ZONES.some((z) => z.value === prefs.timezone) || !prefs.timezone
      ? US_TIME_ZONES
      : [{ value: prefs.timezone, label: prefs.timezone }, ...US_TIME_ZONES];

  return (
    <>
      <Dialog.Title style={[type.h3, { color: colors.text }]}>{titles[editing]}</Dialog.Title>
      <Dialog.ScrollArea style={styles.scrollArea}>
        <ScrollView contentContainerStyle={styles.dialogBody}>
          {editing === "teams" ? (
            <>
              <TeamPicker teams={teams} selected={favorites} onChange={setFavorites} />
              <HelperText type="error" visible={favorites.length === 0}>
                Keep at least one team.
              </HelperText>
            </>
          ) : null}
          {editing === "zip" ? <ZipField userId={userId} value={zip} onChange={setZip} /> : null}
          {editing === "travel" ? (
            <PreferenceSelector
              label="Travel"
              options={TRAVEL_OPTIONS}
              value={travel}
              onChange={setTravel}
            />
          ) : null}
          {editing === "spending" ? (
            <>
              <PreferenceSelector
                label="Spending"
                options={SPENDING_OPTIONS}
                value={spending}
                onChange={setSpending}
              />
              <TextInput
                mode="outlined"
                dense
                label="Max ticket price (optional)"
                value={maxPrice}
                onChangeText={(t) => setMaxPrice(t.replace(/[^\d]/g, ""))}
                keyboardType="number-pad"
                left={<TextInput.Affix text="$" />}
                error={!max.success}
                accessibilityLabel="Max ticket price in dollars"
              />
              <HelperText type={max.success ? "info" : "error"}>
                {max.success ? COPY.maxPriceNote : max.error.issues[0]?.message}
              </HelperText>
            </>
          ) : null}
          {editing === "viewing" ? (
            <PreferenceSelector
              label="Viewing"
              options={VIEWING_OPTIONS}
              value={viewing}
              onChange={setViewing}
              cards
            />
          ) : null}
          {editing === "timezone" ? (
            <RadioButton.Group value={timezone} onValueChange={setTimezone}>
              {zones.map((z) => (
                <RadioButton.Item
                  key={z.value}
                  value={z.value}
                  label={z.label}
                  labelStyle={[type.body, { color: colors.text }]}
                />
              ))}
            </RadioButton.Group>
          ) : null}
          {editing !== "timezone" ? (
            <Text style={[type.caption, { color: colors.textMuted }]}>
              {COPY.preferenceChangeNote}
            </Text>
          ) : null}
        </ScrollView>
      </Dialog.ScrollArea>
      <Dialog.Actions>
        <Button onPress={onCancel}>Cancel</Button>
        <Button mode="contained" disabled={!valid} loading={saving} onPress={() => onSave(change)}>
          Save
        </Button>
      </Dialog.Actions>
    </>
  );
}

/** Requires typing DELETE (UI/UX §5.4, FR-A4). */
function DeleteAccountDialog({
  visible,
  onDismiss,
  onDeleted,
}: {
  visible: boolean;
  onDismiss: () => void;
  onDeleted: () => void;
}) {
  const remove = useDeleteAccount();
  const queryClient = useQueryClient();
  const [confirm, setConfirm] = useState("");
  const [failed, setFailed] = useState<string | null>(null);

  const submit = async () => {
    setFailed(null);
    try {
      // Any request after the delete would provision the account again (FR-A4): stop reloads
      // first, and sign out straight after.
      await queryClient.cancelQueries();
      queryClient.getQueryCache().clear();
      await remove.mutateAsync();
      onDeleted();
    } catch (error) {
      setFailed(
        error instanceof ApiError && error.code === "auth_deletion_failed"
          ? "Your data was deleted, but we couldn't close your sign-in. Try again."
          : COPY.genericError,
      );
    }
  };

  return (
    <Portal>
      <Dialog visible={visible} onDismiss={onDismiss} style={styles.dialog}>
        <Dialog.Title style={[type.h3, { color: colors.text }]}>Delete your account?</Dialog.Title>
        <Dialog.Content style={styles.dialogBody}>
          <Text style={[type.body, { color: colors.textMuted }]}>
            {
              "This deletes your preferences, plans, chats, alerts and notifications, and your sign-in. It can't be undone."
            }
          </Text>
          <TextInput
            mode="outlined"
            dense
            label="Type DELETE to confirm"
            value={confirm}
            onChangeText={setConfirm}
            autoCapitalize="characters"
            accessibilityLabel="Type DELETE to confirm"
          />
          {failed ? <HelperText type="error">{failed}</HelperText> : null}
        </Dialog.Content>
        <Dialog.Actions>
          <Button onPress={onDismiss}>Cancel</Button>
          <Button
            mode="contained"
            buttonColor={colors.danger}
            textColor={colors.onPrimary}
            disabled={confirm !== "DELETE"}
            loading={remove.isPending}
            onPress={() => void submit()}
          >
            {failed ? "Try again" : "Delete account"}
          </Button>
        </Dialog.Actions>
      </Dialog>
    </Portal>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "center" },
  section: { gap: spacing.sm },
  dialog: {
    backgroundColor: colors.surfaceRaised,
    maxWidth: 560,
    width: "92%",
    alignSelf: "center",
  },
  scrollArea: { maxHeight: 480, paddingHorizontal: 0 },
  dialogBody: { gap: spacing.md, padding: spacing.lg },
});
