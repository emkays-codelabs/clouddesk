# CloudDesk user guide: from sign-in to resolution

_Version 1.1 · updated 2026-11-27 · scope: the local Docker environment · checked against the code and the running screens, not against a deployed system._

For support agents using the CloudDesk console. No technical knowledge is needed. Everything here is a demo: refunds and emails are simulated, so nothing real is sent or charged.

## 1. About CloudDesk

CloudDesk reads a support ticket, investigates it (customer, help articles, likely cause), proposes a resolution and a draft reply, and stops for a person before anything that costs money or touches an account. You stay in control: the platform proposes, you decide.

## 2. Before you begin

- CloudDesk must be running, and you need its address (on a local machine, `http://localhost:3000`).
- The demo environment must contain the sample tickets and help articles. The ticket numbers used below (CD-1001 to CD-1013) are **sample tickets supplied by the demo environment**; another environment will not have them.
- The three demo users (Sam, Admin, Vic) are built in.
- Running the AI workflow needs the configured model service to be reachable. If it is not, a run fails and the ticket is handed to a person (section 9).

## 3. Open CloudDesk and sign in

1. Open the address. You land on the CloudDesk home page; choose **Open the console** or **Sign in**.
2. Click one of the three demo users:
   - **Sam (agent)**: can run the AI workflow, approve or reject, reply and escalate. Use this one to follow the guide.
   - **Admin**: everything Sam can do, plus rebuilding the knowledge index.
   - **Vic (viewer)**: can read everything but cannot act. Action buttons are greyed out.
3. You arrive on the **Dashboard**. Your name and role show at the top right. **Home** (top left) returns to the home page and **Sign out** ends your session.
4. A session lasts a fixed eight hours from sign-in, whatever you do. After that you are sent back to sign in.

## 4. Find your way around

| Page | What it is for |
|---|---|
| Dashboard | Open tickets, tickets resolved today, pending approvals and open escalations, a breakdown by severity and by category, and the most recent tickets. |
| Tickets | Every ticket. Search, and filter by status or severity. |
| Approvals | Actions waiting for a person to approve or reject. |
| Customers | A list of customers; open one to see its subscription, workspace, tickets and "What we remember" (the safe notes saved from earlier tickets). |
| Knowledge | The help articles CloudDesk uses as evidence. Search them here. |
| Escalations | Tickets handed to a specialist team, and why. |
| Agents | The six AI agents and run statistics, with cost in USD and INR. |
| Audit | A record of who changed what. |
| Settings | Read-only view of the approval rules. |

## 5. Work a ticket, step by step

1. Open **Tickets** and click a ticket, for example **CD-1010** (a simple feature request).
2. The ticket page has three columns:
   - **Left:** the conversation and a **Reply** box with **Send reply**, **Request info** and **Escalate**. The box grows as you type, up to a maximum height.
   - **Middle:** the **Customer**: company, plan, account status, seats, storage, customer since, region, customer ID and a count of earlier tickets. Click the name for full details.
   - **Right:** **AI workflow**. Its status, progress bar and the **Run AI workflow** button stay at the top while you scroll the page.
3. Click **Run AI workflow**. A message says "Workflow started." The button then reads **Workflow running…** and is disabled until the run ends; afterwards it reads **Run workflow again**. A second run cannot start while one is live.
4. Watch the steps tick over. The platform has twelve possible steps: understand ticket, classify severity, customer context, knowledge retrieval, troubleshooting, resolution planning, risk check, human approval, execute resolution, escalation, ticket summary and memory update. **A single run uses only some of them**: it takes either human approval, execute or escalation depending on the risk check. The home page describes the same journey as ten stages (intake to memory); those are the same work grouped for readers, and the twelve steps here are what the platform actually runs.
5. While a run is going, the panel updates by itself every two seconds and shows an overall status (Running, Waiting for approval, Completed, Escalated or Failed), a step count and a progress bar; it stops updating when the run ends. A run usually takes one to two minutes with the real model.
6. Read the result (section 6), edit the draft in the **Reply** box if needed, then click **Send reply** (the email is simulated).

## 6. Understanding the AI result

The right-hand panel is organised in sections. Approval and escalation notices come first, then these, each of which you can collapse:

| Section | Meaning |
|---|---|
| Chips under the progress bar | The **category**, **severity** (low, medium, high or critical; rules can raise it, never lower it), **risk** (low, medium or high: how sensitive it would be to act; high means a person must look first) and the tokens used. |
| Evidence | Help-article passages the platform used. Each card shows a **Strong match** or **Partial match** label, the real score, a short excerpt, **Show full passage** to read the whole passage, and **View source article**. A **Partial match** is related but not conclusive: do not rely on it alone. Fewer than five cards, or none, is normal when little is relevant. |
| Diagnosis and recommended actions | **Diagnosis** (the likely problem and causes), numbered **Recommended actions** with repeats removed, and a separate **Safety restrictions** box for things that must not be done. |
| Actions | What the platform proposes to do. Refunds and setting resets need your approval. |
| Summary | A short summary of the ticket and what happened. When the run ends, safe notes about the customer are saved for next time. |
| Timeline | Every step, tool call and model call with its time. Collapsed until you open it. |

If the Evidence section says "No sufficiently relevant evidence was found", do not treat the diagnosis as confirmed.

**Always review the recommendation before sending it or approving anything.** The platform can be wrong.

## 7. Approving or rejecting an action

Refunds and setting resets never run on their own.

1. Open **CD-1002** (a refund for unused seats) and click **Run AI workflow**.
2. The run stops and the ticket becomes **waiting on approval**. A yellow box shows what would change: the action, the **amount in INR**, the risk and the reason. Check these, and the evidence, before you decide.
3. Choose:

| Choice | What happens |
|---|---|
| **Approve** | The requested action runs once. It cannot run twice, even if the run is retried. |
| **Reject** | The action is cancelled and the ticket is escalated to a human team. |
| Leave it pending | The ticket stays waiting. Nothing runs, and the ticket cannot be run again until someone decides. (There is no automatic expiry in this version.) |

4. The same request appears on the **Approvals** page.

## 8. Escalations

Security incidents (CD-1005), data loss (CD-1006), account deletion (CD-1009), payment disputes (CD-1011), enterprise outages and suspicious instructions in a ticket (CD-1013) are handed to a named team automatically. The ticket shows **Escalated** with the reason, and the case appears on **Escalations**. You can also click **Escalate** yourself at any time.

**Escalation does not mean the issue is resolved.** It means the case has been routed to the right human team for investigation.

To ask the customer for more detail, click **Request info**. The ticket moves to **waiting on customer**.

## 9. If the AI workflow has a problem

- **The run fails** (for example the model service is down): the ticket is escalated to a person rather than left stuck, and the panel shows the error. Start a new run with **Run again** only after the problem is fixed.
- **The platform is unsure** on a serious ticket (confidence below 0.6): it escalates instead of guessing.
- **There is little or no evidence** (the Evidence section is empty or every card is a Partial match): do not treat the diagnosis as confirmed. Check the **Knowledge** page, or escalate.
- **The run is slow:** with a real model each step can take tens of seconds. Do not start another run while one is going; the button is disabled while a run is active.
- **The button is disabled:** a run is active, the ticket is waiting for approval, or you are signed in as the viewer.
- **A "not allowed" message (409):** someone already decided or started it. Refresh the page.
- **A network banner:** the server cannot be reached. The page retries by itself.
- **"Your session expired":** sign in again.

## 10. Finish

1. After you send a reply or approve an action, the ticket status updates (for example **resolved**).
2. The platform writes a short ticket summary and saves safe notes about the customer for next time. It never stores card numbers, keys or passwords.
3. Check **Audit** for the record of what was done, then click **Sign out**.

## 11. Money you will see

- **Action amounts** (such as a refund) are the business value of the proposed action, shown in **INR**.
- **Model cost** on the **Agents** page is shown in **USD and INR together**. It is labelled **Actual cost** when the provider reported it, **Est. cost** when it comes from a verified price (for example `openai/gpt-oss-120b-Turbo`), and **Cost unavailable** when tokens were used but no price is verified (the plan-hosted `euri-*` models). It is never shown as zero when it is unknown. It is separate from any refund.

## 12. Glossary

| Term | Meaning |
|---|---|
| Workflow | The steps the platform follows to investigate and handle one ticket. |
| Evidence | Retrieved help-article passages that support a recommendation, labelled strong or partial. |
| Diagnosis | The platform's assessment of the likely cause. |
| Severity | How urgent or important the issue is. |
| Risk | How sensitive it would be to act on the issue. |
| Approval | A person's authorisation before a controlled action runs. |
| Escalation | Handing a case to a human specialist team. |
| Memory | Safe customer notes kept to help future tickets. |
| Audit | The record of actions and decisions. |
| Model cost | The cost of the AI model's usage: actual, estimated, or unavailable when no verified price exists. |
