import { ApiError, ApiNetworkError } from "@gamedaygo/api-client";
import { COPY } from "@gamedaygo/shared";
import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { Button, Icon } from "react-native-paper";

import { colors, spacing, type } from "../theme/tokens";
import { Panel } from "./Panel";

const SKELETON_DELAY_MS = 300;

/** Shape-matched grey blocks, shown only when loading takes over 300 ms (UI/UX §5.3).
 * No shimmer, so nothing moves for reduce-motion users. */
export function Skeleton({ rows = 3, height = 96 }: { rows?: number; height?: number }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), SKELETON_DELAY_MS);
    return () => clearTimeout(timer);
  }, []);
  if (!visible) return null;
  return (
    <View accessibilityLabel="Loading" accessibilityRole="progressbar" style={styles.skeletons}>
      {Array.from({ length: rows }, (_, i) => (
        <View key={i} style={[styles.skeleton, { height }]} />
      ))}
    </View>
  );
}

interface EmptyStateProps {
  icon: string;
  title: string;
  body?: string;
  action?: { label: string; onPress: () => void };
}

/** Says why there's nothing and what next, never just "No data" (UI/UX §5.3). */
export function EmptyState({ icon, title, body, action }: EmptyStateProps) {
  return (
    <Panel variant="glass" style={styles.center}>
      <Icon source={icon} size={48} color={colors.textSubtle} />
      <Text style={[type.h3, styles.text]} accessibilityRole="header">
        {title}
      </Text>
      {body ? <Text style={[type.body, styles.muted]}>{body}</Text> : null}
      {action ? (
        <Button mode="outlined" onPress={action.onPress}>
          {action.label}
        </Button>
      ) : null}
    </Panel>
  );
}

/** Plain-language failure with Try again; the request ID sits behind "Details". */
export function ErrorState({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const [details, setDetails] = useState(false);
  const offline = error instanceof ApiNetworkError;
  const requestId = error instanceof ApiError ? error.requestId : null;
  return (
    <Panel variant="glass" style={styles.center}>
      <Icon
        source={offline ? "wifi-off" : "alert-circle-outline"}
        size={48}
        color={colors.danger}
      />
      <Text style={[type.h3, styles.text]} accessibilityRole="header">
        {offline ? "Can't reach GameDay Go" : COPY.genericError}
      </Text>
      {offline ? (
        <Text style={[type.body, styles.muted]}>Check your connection and try again.</Text>
      ) : null}
      <Button mode="outlined" onPress={onRetry}>
        Try again
      </Button>
      {requestId ? (
        details ? (
          <Text style={[type.caption, styles.muted]} selectable>
            Request ID: {requestId}
          </Text>
        ) : (
          <Button compact onPress={() => setDetails(true)}>
            Details
          </Button>
        )
      ) : null}
    </Panel>
  );
}

/** Shown when cached data is on screen but the latest reload couldn't reach the server. */
export function OfflineBanner({ visible }: { visible: boolean }) {
  if (!visible) return null;
  return (
    <View style={styles.banner} accessibilityRole="alert">
      <Icon source="wifi-off" size={18} color={colors.text} />
      <Text style={[type.caption, styles.text]}>{COPY.offline}</Text>
    </View>
  );
}

export function isOffline(query: { data?: unknown; error: unknown }): boolean {
  return query.data !== undefined && query.error instanceof ApiNetworkError;
}

const styles = StyleSheet.create({
  skeletons: { gap: spacing.md },
  skeleton: { backgroundColor: colors.surfaceRaised, opacity: 0.8 },
  center: { alignItems: "center", gap: spacing.md, paddingVertical: spacing.xl },
  text: { color: colors.text, textAlign: "center" },
  muted: { color: colors.textMuted, textAlign: "center" },
  banner: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    padding: spacing.md,
    backgroundColor: colors.surfaceRaised,
    borderLeftWidth: 3,
    borderLeftColor: colors.info,
  },
});
