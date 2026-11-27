# CloudDesk user guide: from sign-in to resolution

_Version 1.0 · written 2026-11-27 · scope: the local demo environment · checked against the code, not against a deployed system._

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
| Dashboard | Counts of tickets by status, and what needs attention. |
| Tickets | Every ticket. Search, and filter by status or severity. |
| Approvals | Actions waiting for a person to approve or reject. |
| Customers | Customer details, their plan, earlier tickets and saved notes. |
| Knowledge | The help articles CloudDesk uses as evidence. Search them here. |
| Escalations | Tickets handed to a specialist team, and why. |
| Agents | The six AI agents and run statistics, with cost in USD and INR. |
| Audit | A record of who changed what. |
| Settings | Read-only view of the approval rules. |

## 5. Work a ticket, step by step

1. Open **Tickets** and click a ticket, for example **CD-1010** (a simple feature request).
2. The ticket page has three columns:
   - **Left:** the conversation and a **Reply** box with **Send reply**, **Request info** and **Escalate**.
   - **Middle:** the **Customer**: company, plan, seats, storage and earlier tickets. Click the name for full details.
   - **Right:** **AI workflow**.
3. Click **Run AI workflow**. A message says "Workflow started."
4. Watch the steps tick over. The platform has twelve possible steps: understand ticket, classify severity, customer context, knowledge retrieval, troubleshooting, resolution planning, risk check, human approval, execute resolution, escalation, ticket summary and memory update. **A single run uses only some of them**: it takes either human approval, execute or escalation depending on the risk check. The home page describes the same journey as ten stages (intake to memory); those are the same work grouped for readers, and the twelve steps here are what the platform actually runs.
5. While a run is going, the panel updates by itself every two seconds; it stops updating when the run ends. A run can take seconds, or minutes with a real model.
6. Read the result (section 6), edit the draft in the **Reply** box if needed, then click **Send reply** (the email is simulated).

## 6. Understanding the AI result

| Item | Meaning |
|---|---|
| Category | The type of issue, for example billing or login issue. |
| Severity | How urgent the ticket is: low, medium, high or critical. Rules can raise it, never lower it. |
| Risk | Low, medium or high: how sensitive it would be to act. High means a person must look first. |
| Tokens | How much text the model processed. |
| Evidence | Help-article passages the platform used, each with a score and a link. |
| Diagnosis | The likely cause and numbered steps to try. |
| Planned actions | What the platform proposes to do. Refunds and setting resets need your approval. |
| Draft reply | A suggested customer reply built from the evidence. |

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
- **There is little or no evidence:** do not treat the diagnosis as confirmed. Check the **Knowledge** page, or escalate.
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
- **Model cost** on the **Agents** page is the estimated cost of using the AI model, always shown in **USD and INR together** at a fixed display rate. It is an estimate and is separate from any refund.

## 12. Glossary

| Term | Meaning |
|---|---|
| Workflow | The steps the platform follows to investigate and handle one ticket. |
| Evidence | Retrieved help-article passages that support a recommendation. |
| Diagnosis | The platform's assessment of the likely cause. |
| Severity | How urgent or important the issue is. |
| Risk | How sensitive it would be to act on the issue. |
| Approval | A person's authorisation before a controlled action runs. |
| Escalation | Handing a case to a human specialist team. |
| Memory | Safe customer notes kept to help future tickets. |
| Audit | The record of actions and decisions. |
| Model cost | The estimated cost of the AI model's usage. |
