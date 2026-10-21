import { signInSchema, signUpSchema } from "./auth";

const valid = {
  email: "ben@example.com",
  password: "bears2026",
  confirmPassword: "bears2026",
  ageConfirmed: true,
};

function issues(values: unknown): Record<string, string> {
  const result = signUpSchema.safeParse(values);
  if (result.success) return {};
  return Object.fromEntries(result.error.issues.map((i) => [i.path.join("."), i.message]));
}

describe("signUpSchema", () => {
  it("accepts valid values", () => {
    expect(signUpSchema.safeParse(valid).success).toBe(true);
  });

  it("requires the 18+ confirmation (FR-A3)", () => {
    expect(issues({ ...valid, ageConfirmed: false })).toEqual({
      ageConfirmed: "You must be 18 or older to use GameDay Go",
    });
  });

  it("enforces the password policy", () => {
    expect(issues({ ...valid, password: "short1", confirmPassword: "short1" }).password).toBe(
      "Use at least 8 characters",
    );
    expect(
      issues({ ...valid, password: "lettersonly", confirmPassword: "lettersonly" }).password,
    ).toBe("Include at least one number");
  });

  it("requires matching passwords", () => {
    expect(issues({ ...valid, confirmPassword: "bears2027" })).toEqual({
      confirmPassword: "Passwords don't match",
    });
  });

  it("rejects an invalid email", () => {
    expect(issues({ ...valid, email: "not-an-email" }).email).toBe("Enter a valid email address");
  });
});

describe("signInSchema", () => {
  it("trims the email and requires a password", () => {
    expect(signInSchema.parse({ email: " ben@example.com ", password: "x" }).email).toBe(
      "ben@example.com",
    );
    expect(signInSchema.safeParse({ email: "ben@example.com", password: "" }).success).toBe(false);
  });
});
