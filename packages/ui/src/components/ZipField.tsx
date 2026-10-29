import { ApiError, useNearestZip, useZipLookup } from "@gamedaygo/api-client";
import { COPY } from "@gamedaygo/shared";
import * as Location from "expo-location";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { Button, HelperText, TextInput } from "react-native-paper";

import { colors, spacing, type } from "../theme/tokens";

interface ZipFieldProps {
  userId: string | null;
  value: string;
  onChange: (zip: string) => void;
}

/** 5-digit ZIP checked against the ZIP dataset as you type, with "Use my location" (FR-P3). */
export function ZipField({ userId, value, onChange }: ZipFieldProps) {
  const lookup = useZipLookup(userId, value);
  const nearest = useNearestZip();
  const [locationNote, setLocationNote] = useState<string | null>(null);

  const locate = async () => {
    setLocationNote(null);
    try {
      // Permission is requested only now, on tap (FR-P3).
      const permission = await Location.requestForegroundPermissionsAsync();
      if (permission.status !== "granted") {
        setLocationNote(COPY.locationDenied);
        return;
      }
      const position = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      // Coordinates stay in this handler: sent once, never stored (FR-P3a).
      const zip = await nearest.mutateAsync({
        lat: position.coords.latitude,
        lng: position.coords.longitude,
      });
      onChange(zip.zip);
    } catch (error) {
      setLocationNote(
        error instanceof ApiError && error.status === 404
          ? "We couldn't find a US ZIP near you. Enter your ZIP instead."
          : COPY.locationDenied,
      );
    }
  };

  const complete = /^\d{5}$/.test(value);
  // Only a 404 means the ZIP doesn't exist; other failures shouldn't blame the user's input.
  const notFound = complete && lookup.error instanceof ApiError && lookup.error.status === 404;
  const lookupFailed = complete && lookup.isError && !notFound;
  return (
    <View style={styles.field}>
      <Text style={[type.label, { color: colors.textMuted }]}>ZIP code</Text>
      <TextInput
        mode="outlined"
        dense
        value={value}
        onChangeText={(text) => onChange(text.replace(/\D/g, "").slice(0, 5))}
        keyboardType="number-pad"
        autoComplete="postal-code"
        textContentType="postalCode"
        maxLength={5}
        accessibilityLabel="ZIP code"
        error={notFound}
      />
      {complete && lookup.data ? (
        <Text style={[type.body, { color: colors.success }]} accessibilityLiveRegion="polite">
          {lookup.data.place_name}, {lookup.data.state}
        </Text>
      ) : null}
      <HelperText type="error" visible={notFound || lookupFailed} style={styles.helper}>
        {notFound ? COPY.zipNotFound : "Couldn't check that ZIP. Check your connection."}
      </HelperText>
      <Button
        mode="text"
        icon="crosshairs-gps"
        onPress={() => void locate()}
        loading={nearest.isPending}
        style={styles.location}
      >
        Use my location
      </Button>
      {locationNote ? (
        <Text style={[type.caption, { color: colors.textMuted }]}>{locationNote}</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  field: { gap: spacing.xs },
  helper: { paddingHorizontal: 0 },
  location: { alignSelf: "flex-start", marginLeft: -spacing.md },
});
