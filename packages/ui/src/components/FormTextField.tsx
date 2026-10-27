import type { ComponentProps } from "react";
import { Controller, type Control, type FieldValues, type Path } from "react-hook-form";
import { StyleSheet, Text, View } from "react-native";
import { HelperText, TextInput } from "react-native-paper";

import { colors, spacing, type } from "../theme/tokens";

type TextInputProps = Omit<
  ComponentProps<typeof TextInput>,
  "value" | "onChangeText" | "error" | "label"
>;

interface FormTextFieldProps<T extends FieldValues> extends TextInputProps {
  control: Control<T>;
  name: Path<T>;
  label: string;
}

/**
 * Paper text input bound to React Hook Form, with a fixed label above it and the error inline
 * under it. The label sits outside the field (not floating inside it) because browser autofill
 * fills values without notifying the app, which would leave a floating label overlapping them.
 */
export function FormTextField<T extends FieldValues>({
  control,
  name,
  label,
  ...inputProps
}: FormTextFieldProps<T>) {
  return (
    <Controller
      control={control}
      name={name}
      render={({ field: { value, onChange, onBlur }, fieldState: { error } }) => (
        <View style={styles.field}>
          <Text style={styles.label} accessibilityElementsHidden importantForAccessibility="no">
            {label}
          </Text>
          <TextInput
            mode="outlined"
            value={(value as string | undefined) ?? ""}
            onChangeText={onChange}
            onBlur={onBlur}
            error={!!error}
            accessibilityLabel={label}
            dense
            {...inputProps}
          />
          <HelperText type="error" visible={!!error} style={styles.helper}>
            {error?.message}
          </HelperText>
        </View>
      )}
    />
  );
}

const styles = StyleSheet.create({
  field: { gap: spacing.xs },
  label: { ...type.label, color: colors.textMuted },
  helper: { paddingHorizontal: 0 },
});
