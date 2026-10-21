import type { ComponentProps } from "react";
import { Controller, type Control, type FieldValues, type Path } from "react-hook-form";
import { View } from "react-native";
import { HelperText, TextInput } from "react-native-paper";

type TextInputProps = Omit<ComponentProps<typeof TextInput>, "value" | "onChangeText" | "error">;

interface FormTextFieldProps<T extends FieldValues> extends TextInputProps {
  control: Control<T>;
  name: Path<T>;
}

/** Paper text input bound to React Hook Form, with the error shown inline under the field. */
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
        <View>
          <TextInput
            mode="outlined"
            label={label}
            value={(value as string | undefined) ?? ""}
            onChangeText={onChange}
            onBlur={onBlur}
            error={!!error}
            accessibilityLabel={typeof label === "string" ? label : undefined}
            {...inputProps}
          />
          <HelperText type="error" visible={!!error}>
            {error?.message}
          </HelperText>
        </View>
      )}
    />
  );
}
