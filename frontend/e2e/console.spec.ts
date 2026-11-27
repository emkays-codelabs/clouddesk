import { expect, test } from "@playwright/test";

/** Needs the stack up (docker compose) and the frontend on FRONTEND_URL (default :3000). */
test("landing, sign in as an agent, open a ticket and run the workflow", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Resolve beyond/ })).toBeVisible();
  await page.getByRole("link", { name: "Sign in" }).first().click();

  await expect(page.getByText("Choose a demo user.")).toBeVisible();
  await page.getByRole("button", { name: /Sam \(agent\)/ }).click();
  await page.waitForURL("**/dashboard");

  await page.getByRole("link", { name: "Tickets" }).first().click();
  await page.waitForURL("**/tickets");
  await page.getByRole("link", { name: /CD-1010/ }).first().click();
  await expect(page.getByText("CD-1010").first()).toBeVisible();

  await page.getByRole("button", { name: /Run AI workflow|Run again/ }).click();
  await expect(page.getByText("Workflow started.")).toBeVisible();
  // The real model is slow: wait for the run to finish, or to stop for a person.
  await expect(page.getByText(/completed|waiting for approval|escalated/i).first()).toBeVisible({
    timeout: 360_000,
  });

  await page.getByRole("link", { name: "Agents" }).first().click();
  await expect(page.getByText(/Est\. cost/)).toBeVisible();
  await page.screenshot({ path: "e2e/last-run.png", fullPage: true });
});

test("a viewer cannot run workflows", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: /Vic \(viewer\)/ }).click();
  await page.waitForURL("**/dashboard");
  await page.getByRole("link", { name: "Tickets" }).first().click();
  await page.getByRole("link", { name: /CD-1010/ }).first().click();
  await expect(page.getByRole("button", { name: /Run AI workflow|Run again/ })).toBeDisabled();
});
