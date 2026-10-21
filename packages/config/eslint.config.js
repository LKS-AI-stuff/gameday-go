// Shared ESLint flat config for apps and packages.
const expoConfig = require("eslint-config-expo/flat");

module.exports = [
  ...expoConfig,
  {
    ignores: ["dist/**", ".expo/**", "**/schema.d.ts"],
  },
];
