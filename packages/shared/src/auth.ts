import { z } from "zod";

// Matches the local and hosted Supabase Auth password policy (supabase/config.toml).
export const MIN_PASSWORD_LENGTH = 8;

const email = z
  .string()
  .trim()
  .pipe(z.email({ error: "Enter a valid email address" }));

export const signInSchema = z.object({
  email,
  password: z.string().min(1, { error: "Enter your password" }),
});
export type SignInValues = z.infer<typeof signInSchema>;

export const signUpSchema = z
  .object({
    email,
    password: z
      .string()
      .min(MIN_PASSWORD_LENGTH, { error: `Use at least ${MIN_PASSWORD_LENGTH} characters` })
      .regex(/[A-Za-z]/, { error: "Include at least one letter" })
      .regex(/\d/, { error: "Include at least one number" }),
    confirmPassword: z.string(),
    // FR-A3: users must confirm they are 18 or older at sign-up.
    ageConfirmed: z
      .boolean()
      .refine((v) => v, { error: "You must be 18 or older to use GameDay Go" }),
  })
  .refine((v) => v.password === v.confirmPassword, {
    error: "Passwords don't match",
    path: ["confirmPassword"],
  });
export type SignUpValues = z.infer<typeof signUpSchema>;
