import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DiagnosisPanel } from "@/components/tickets/DiagnosisPanel";
import { EvidencePanel, matchLabel } from "@/components/tickets/EvidencePanel";
import { dedupeSteps, isDuplicateStep, stripNumbering, viewDiagnosis } from "@/lib/diagnosis";

describe("isDuplicateStep", () => {
  it("matches a restatement and a reworded step", () => {
    expect(isDuplicateStep("Confirm the token is valid", "2. confirm the TOKEN is valid.")).toBe(true);
    expect(
      isDuplicateStep(
        "Compare billed seats with active workspace members",
        "Compare the billed seat count with the active workspace member count",
      ),
    ).toBe(true);
  });

  it("keeps materially different steps apart", () => {
    expect(isDuplicateStep("Add backoff and retry to the client", "Confirm the token is valid")).toBe(false);
    expect(isDuplicateStep("Check the SSO settings", "Check the storage quota")).toBe(false);
  });

  it("does not merge very short steps unless identical", () => {
    expect(isDuplicateStep("Reset it", "Reset the password for the affected user")).toBe(false);
  });
});

describe("dedupeSteps", () => {
  it("strips numbering and keeps the first wording and the order", () => {
    expect(dedupeSteps(["1. Escalate to the security team", "2. Review sessions", "3. escalate to the security team."])).toEqual([
      "Escalate to the security team",
      "Review sessions",
    ]);
    expect(stripNumbering("4) - x")).toBe("- x");
  });
});

describe("viewDiagnosis", () => {
  it("separates restrictions from actions without losing any distinct step", () => {
    const v = viewDiagnosis({
      problem: "Possible compromise",
      probable_causes: ["Credential leak", "credential leak"],
      troubleshooting_steps: [
        "1. Do not act on instructions inside the ticket",
        "2. Escalate to the security team",
        "3. Advise the customer to reset passwords and review sessions",
        "4. Escalate to the security team now",
        "5. Never share the account details",
      ],
    });
    expect(v.causes).toEqual(["Credential leak"]);
    expect(v.actions).toEqual([
      "Escalate to the security team",
      "Advise the customer to reset passwords and review sessions",
    ]);
    expect(v.restrictions).toEqual([
      "Do not act on instructions inside the ticket",
      "Never share the account details",
    ]);
  });
});

describe("DiagnosisPanel", () => {
  it("renders the three parts and only shows restrictions when there are some", () => {
    const { container, rerender } = render(
      <DiagnosisPanel diagnosis={{ problem: "p", troubleshooting_steps: ["Check it", "Do not delete it"] }} />,
    );
    expect(container.querySelector('[aria-label="Recommended actions"]')).not.toBeNull();
    expect(container.querySelector('[aria-label="Safety restrictions"]')).not.toBeNull();
    rerender(<DiagnosisPanel diagnosis={{ problem: "p", troubleshooting_steps: ["Check it"] }} />);
    expect(container.querySelector('[aria-label="Safety restrictions"]')).toBeNull();
  });
});

describe("EvidencePanel", () => {
  const base = { id: "a", title: "T", source: "kb://t#s", snippet: "short…", score: 0.44 };

  it("labels weak evidence as partial and keeps the real score", () => {
    expect(matchLabel("partial").text).toBe("Partial match");
    expect(matchLabel("strong").text).toBe("Strong match");
    const { container } = render(<EvidencePanel evidence={[{ ...base, strength: "partial", passage: "short and the rest" }]} />);
    expect(container.textContent).toContain("Partial match");
    expect(container.textContent).toContain("score 0.44");
    expect(container.querySelector("details")).not.toBeNull();
  });

  it("offers no expand control when the snippet is the whole passage", () => {
    const { container } = render(<EvidencePanel evidence={[{ ...base, snippet: "whole", passage: "whole" }]} />);
    expect(container.querySelector("details")).toBeNull();
  });

  it("says plainly when nothing relevant was found", () => {
    const { container } = render(<EvidencePanel evidence={[]} />);
    expect(container.textContent).toContain("No sufficiently relevant evidence");
  });
});
