import { expect, test } from "vitest";
test("test runner is configured", () =>
  expect(document.documentElement).toBeInTheDocument());
