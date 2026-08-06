import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    globals: true,
    environment: "node",
    include: ["tests/**/*.test.js"],
    // The repo currently has no JS functions (the contact handler moved out),
    // so there are no JS tests. Without this, `vitest run` exits 1 and blocks
    // the validate gate. Remove once a JS function and its tests are back.
    passWithNoTests: true,
  },
});
