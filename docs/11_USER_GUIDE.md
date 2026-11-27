# CloudDesk user guide: from sign-in to resolution

For support agents using the CloudDesk console. No technical knowledge is needed. Everything here is a demo: refunds and emails are simulated, so nothing real is sent or charged.

## 1. Open CloudDesk

1. Ask whoever runs the stack for the address (on a local machine it is `http://localhost:3000`).
2. You land on the CloudDesk home page. Read it if you like, then choose **Open the console** or **Sign in**.

## 2. Sign in

1. On the sign-in page you will see three demo users. Click one:
   - **Sam (agent)**: can run the AI workflow, approve or reject, reply and escalate. Use this one to follow the guide.
   - **Admin**: everything Sam can do, plus rebuilding the knowledge index.
   - **Vic (viewer)**: can read everything but cannot act. Action buttons are greyed out.
2. You arrive on the **Dashboard**. Your name and role show at the top right. **Home** (top left) returns to the home page and **Sign out** ends your session. Sessions last about eight hours; if one expires you are sent back to sign in.

## 3. Find your way around

The left menu has nine pages:

| Page | What it is for |
|---|---|
| Dashboard | Counts of tickets by status, and what needs attention. |
| Tickets | Every ticket. Search, and filter by status or severity. |
| Approvals | Actions waiting for a person to approve or reject. |
| Customers | Customer details, their plan, and earlier tickets. |
| Knowledge | The help articles CloudDesk uses as evidence. Search them here. |
| Escalations | Tickets handed to a specialist team, and why. |
| Agents | The six AI agents and run statistics, with cost in USD and INR. |
| Audit | A record of who changed what. |
| Settings | Read-only view of the approval rules. |

## 4. Work a ticket, step by step

1. Open **Tickets** and click a ticket, for example **CD-1010** (a simple feature request).
2. The ticket page has three columns:
   - **Left:** the conversation and a **Reply** box with the buttons **Send reply**, **Request info** and **Escalate**.
   - **Middle:** the **Customer**: company, plan, seats, storage and earlier tickets. Click the name for full details.
   - **Right:** **AI workflow**.
3. Click **Run AI workflow**. A message says "Workflow started."
4. Watch the twelve steps tick over: understand, classify, customer context, knowledge retrieval, troubleshooting, resolution planning, risk check, then execute or escalate, summary and memory update. The page refreshes by itself every two seconds. A run can take from a few seconds to a few minutes when a real model is connected.
5. When it finishes, read the right column:
   - Chips show the **category**, **severity**, **risk** and tokens used.
   - **Evidence** lists the help articles used, each with a score and a link.
   - **Diagnosis** gives the likely problem and numbered steps.
   - **Planned actions** list what the platform proposes to do.
   - A draft reply appears for you to edit.
6. Edit the draft in the **Reply** box if needed, then click **Send reply** (the email is simulated).

## 5. When the platform asks for your approval

Refunds and setting resets never run on their own.

1. Open **CD-1002** (the refund for unused seats) and click **Run AI workflow**.
2. The run stops and the ticket becomes **waiting on approval**. A yellow box says **Waiting for your approval** and shows exactly what would change, the amount (in INR) and the risk.
3. Click **Approve** to let the action run once, or **Reject** to cancel it. Rejecting escalates the ticket to a human team.
4. The same request also appears on the **Approvals** page.
5. A ticket that is waiting cannot be run again until you decide.

## 6. Cases the platform always escalates

Security incidents (CD-1005), data loss (CD-1006), account deletion (CD-1009), payment disputes (CD-1011), enterprise outages and suspicious instructions in a ticket (CD-1013) are handed to a named team automatically. The ticket shows **Escalated** with the reason, and the case appears on the **Escalations** page. Use **Escalate** yourself at any time if you are unsure.

## 7. Ask the customer for more detail

Click **Request info** to send a standard question to the customer. The ticket moves to **waiting on customer**.

## 8. Finish

1. After you send a reply or approve an action, the ticket status updates (for example **resolved**).
2. The platform writes a short ticket summary and saves safe notes about the customer for next time. It never stores card numbers, keys or passwords.
3. Check **Audit** to see the record of what was done, then click **Sign out**.

## 9. If something looks wrong

| You see | What to do |
|---|---|
| Buttons are greyed out | You are signed in as the viewer. Sign out and use Sam or Admin. |
| "Your session expired" | Sign in again. |
| A banner about the network | The server is unreachable. The page retries by itself; ask whoever runs the stack. |
| Run again is disabled | The ticket is waiting for approval, or a run is still going. |
| A message saying the action is not allowed (409) | Someone already decided or started it. Refresh the page. |

## 10. Words used in CloudDesk

- **Workflow:** the twelve steps the platform follows for one ticket.
- **Evidence:** help-article passages the platform quotes, with a score.
- **Risk:** low, medium or high. High means a person must look first.
- **Escalation:** handing a ticket to a specialist team.
- **Cost:** shown in US dollars and Indian rupees together; it is an estimate.
