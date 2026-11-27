"""Run one demo ticket through the support workflow in the terminal (P11-5, F9, F10, F14).

Usage:  make demo                      CD-1002: a refund, which pauses for your approval
        make demo TICKET=CD-1005       a security ticket, which escalates by policy

It starts the real app in this process (no server to run), signs in as the demo agent, runs the
workflow and prints every step. A ticket that needs approval stops and asks you: type `y` to approve
(the refund is then recorded once) or anything else to reject (the ticket escalates instead).
It uses the offline fake language model unless DEMO_REAL_LLM=1, so it needs no key and no network.
Set DEMO_DECISION=approve|reject to answer the question without a prompt.
"""

import os
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT / "backend", ROOT):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

AGENT_EMAIL = "sam.agent@clouddesk.demo"


def _ask_decision() -> str:
    preset = os.environ.get("DEMO_DECISION", "").strip().lower()
    if preset in ("approve", "reject"):
        return preset
    answer = input("Approve this action? [y/N] ").strip().lower()
    return "approve" if answer in ("y", "yes") else "reject"


def run(
    ticket_number: str,
    decide: Callable[[], str] = _ask_decision,
    out: Callable[[str], None] = print,
) -> dict:
    """Run `ticket_number` and return the final workflow state (the demo's whole story)."""
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app()) as client:
        login = client.post("/api/v1/auth/demo-login", json={"email": AGENT_EMAIL})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        page = client.get("/api/v1/tickets", headers=headers, params={"search": ticket_number})
        found = [t for t in page.json()["items"] if t["ticket_number"] == ticket_number]
        if not found:
            out(f"No ticket {ticket_number}. Run `make seed` first, or pick CD-1001 to CD-1013.")
            return {}
        ticket = found[0]
        out(f"{ticket['ticket_number']}: {ticket['subject']}")
        run_response = client.post(f"/api/v1/tickets/{ticket['id']}/run", headers=headers)
        out(f"run accepted (HTTP {run_response.status_code})")
        state = client.get(f"/api/v1/tickets/{ticket['id']}/workflow", headers=headers).json()
        _print_steps(state, out)

        if state["status"] == "waiting_for_approval":
            pending = client.get(
                "/api/v1/approvals", headers=headers, params={"status": "pending"}
            ).json()
            approval = next(a for a in pending if a["ticket_id"] == ticket["id"])
            action = approval["action"]
            out(f"\nWaiting for you: {action['description']}")
            out(f"  tool: {action['tool']}  arguments: {action['arguments']}")
            verb = decide()
            result = client.post(
                f"/api/v1/approvals/{approval['id']}/{verb}", headers=headers, json={}
            )
            state = result.json()["workflow"]
            out(f"\nYou chose to {verb}. The workflow is now: {state['status']}")
            _print_steps(state, out)

        detail = client.get(f"/api/v1/tickets/{ticket['id']}", headers=headers).json()
        out(f"\nTicket status: {detail['status']}")
        if detail.get("escalation"):
            out(f"Escalated to: {detail['escalation']['assigned_team']}")
        for action in detail["resolution_actions"]:
            out(f"Action {action['tool']}: {action['status']}")
        if state.get("ticket_summary"):
            out(f"Summary: {state['ticket_summary']}")
        return state


def _print_steps(state: dict, out: Callable[[str], None]) -> None:
    for number, node in enumerate(state.get("completed_nodes", []), 1):
        out(f"  {number:>2}. {node}")
    out(f"status: {state.get('status')}")


def main() -> int:
    if os.environ.get("DEMO_REAL_LLM") != "1":
        os.environ["LLM_PROVIDER"] = "fake"
        os.environ["EMBEDDING_PROVIDER"] = "fake"
        os.environ["USE_FAKE_REDIS"] = "true"
    ticket = os.environ.get("TICKET", "CD-1002").strip() or "CD-1002"
    return 0 if run(ticket) else 1


if __name__ == "__main__":
    raise SystemExit(main())
