import { expect, test, type Page } from "@playwright/test";

/** Local end-to-end checks of the whole console. Needs the stack up; headed so you can watch. */

async function signIn(page: Page, who: RegExp) {
  await page.goto("/login");
  await page.getByRole("button", { name: who }).click();
  await page.waitForURL("**/dashboard");
}

async function openTicket(page: Page, number: string) {
  await page.getByRole("link", { name: "Tickets" }).first().click();
  await page.waitForURL("**/tickets");
  await page.getByRole("link", { name: new RegExp(number) }).first().click();
  await expect(page.getByText(number).first()).toBeVisible();
}

const PAGES: ReadonlyArray<readonly [string, string]> = [
  ["Dashboard", "dashboard"],
  ["Tickets", "tickets"],
  ["Approvals", "approvals"],
  ["Customers", "customers"],
  ["Knowledge", "knowledge"],
  ["Escalations", "escalations"],
  ["Agents", "agents"],
  ["Audit", "audit"],
  ["Settings", "settings"],
];

test("every console page loads without an error and is captured", async ({ page }) => {
  await signIn(page, /Admin/);
  for (const [label, slug] of PAGES) {
    await page.getByRole("link", { name: label, exact: true }).first().click();
    await page.waitForURL(`**/${slug}`);
    // Next.js keeps an empty route announcer with role=alert; only an alert with text is an error.
    await expect(page.getByRole("alert").filter({ hasText: /\S/ })).toHaveCount(0);
    await page.waitForTimeout(800);
    await page.screenshot({ path: `e2e/shots/${slug}.png`, fullPage: true });
  }
  await page.goto("/");
  await page.screenshot({ path: "e2e/shots/landing.png", fullPage: true });
});

test("a refund pauses for approval, then Approve runs it", async ({ page }) => {
  await signIn(page, /Sam/);
  await openTicket(page, "CD-1002");
  // The demo data keeps state between runs: a previous run may already be waiting for approval.
  const waiting = page.getByText("Waiting for your approval");
  if (!(await waiting.isVisible().catch(() => false))) {
    await page.getByRole("button", { name: /Run AI workflow|Run workflow again/ }).click();
  }
  await expect(waiting).toBeVisible({ timeout: 360_000 });
  await page.screenshot({ path: "e2e/shots/approval.png", fullPage: true });
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(page.getByText(/Approved/i).first()).toBeVisible();
  await expect(page.getByText("Waiting for your approval")).toHaveCount(0, { timeout: 180_000 });
});

test("a security ticket escalates by policy", async ({ page }) => {
  await signIn(page, /Sam/);
  await openTicket(page, "CD-1005");
  await page.getByRole("button", { name: /Run AI workflow|Run workflow again/ }).click();
  await expect(page.getByText(/Escalated:/)).toBeVisible({ timeout: 360_000 });
  await page.screenshot({ path: "e2e/shots/escalation.png", fullPage: true });
});

test("a viewer sees disabled actions", async ({ page }) => {
  await signIn(page, /Vic/);
  await openTicket(page, "CD-1010");
  await expect(page.getByRole("button", { name: /Send reply/ })).toBeDisabled();
  await expect(page.getByRole("button", { name: /Escalate/ })).toBeDisabled();
});

test("the run button is disabled while a workflow is running", async ({ page }) => {
  await signIn(page, /Sam/);
  await openTicket(page, "CD-1012");
  const run = page.getByRole("button", { name: /Run AI workflow|Run workflow again|Workflow running/ });
  await run.click();
  await expect(page.getByRole("button", { name: /Workflow running/ })).toBeDisabled();
  await expect(page.getByRole("progressbar")).toBeVisible();
  await expect(page.getByRole("button", { name: /Run workflow again/ })).toBeEnabled({ timeout: 360_000 });
});
