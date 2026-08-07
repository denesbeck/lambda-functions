import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    globals: true,
    environment: "node",
    include: ["tests/**/*.test.js"],
    // No JS functions in this repo yet; remove once there are JS tests.
    passWithNoTests: true,
  },
});
