"""
Interactive CLI for the JLL Bid Copilot prototype.

Run with:  python -m app.cli

Commands (typed at the prompt, in addition to normal chat messages):
  /new <client name>          create a new opportunity and switch to it
  /switch <opportunity_id>    switch the active opportunity
  /list                       list known opportunity ids
  /state                      print the full opportunity memory record
  /approvals                  list pending/decided approval requests
  /approve <approval_id>      approve a pending request (acting as the human reviewer)
  /reject <approval_id>       reject a pending request
  /events                     print the pipeline event log
  /quit                       exit
"""
from __future__ import annotations

import json
import sys

from app.approvals import decide_approval
from app.orchestrator import BidCopilotOrchestrator, OrchestratorError
from app.state import ConversationStore, OpportunityStore


def main() -> None:
    opportunity_store = OpportunityStore()
    conversation_store = ConversationStore()

    try:
        orchestrator = BidCopilotOrchestrator(opportunity_store, conversation_store)
    except OrchestratorError as exc:
        print(f"\n[!] {exc}\n")
        sys.exit(1)

    print("JLL Bid & Leasing Copilot — internal prototype (type /quit to exit)")
    active_id = None

    existing = opportunity_store.list_ids()
    if existing:
        print(f"Existing opportunities: {', '.join(existing)}")
        print("Use /switch <id> to resume one, or /new <client name> to start fresh.\n")
    else:
        print("No opportunities yet. Start with: /new <client name>\n")

    while True:
        try:
            line = input(f"[{active_id or '-'}]> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue

        if line.startswith("/quit"):
            break

        if line.startswith("/new "):
            client_name = line[len("/new "):].strip()
            record = opportunity_store.create(client_name)
            active_id = record["opportunity_id"]
            print(f"Created opportunity {active_id} for client '{client_name}'. Stage: {record['stage']}")
            continue

        if line.startswith("/switch "):
            candidate = line[len("/switch "):].strip()
            try:
                opportunity_store.get(candidate)
                active_id = candidate
                print(f"Switched to {active_id}.")
            except Exception:
                print(f"No such opportunity: {candidate}")
            continue

        if line.startswith("/list"):
            ids = opportunity_store.list_ids()
            print("\n".join(ids) if ids else "(none)")
            continue

        if line.startswith("/state"):
            if not active_id:
                print("No active opportunity. Use /new or /switch first.")
                continue
            print(json.dumps(opportunity_store.get(active_id), indent=2))
            continue

        if line.startswith("/events"):
            if not active_id:
                print("No active opportunity. Use /new or /switch first.")
                continue
            record = opportunity_store.get(active_id)
            for ev in record["pipeline_events"]:
                print(f"  [{ev['timestamp']}] {ev['stage']}: {ev['event']}" + (f" (outcome={ev['outcome']})" if ev.get("outcome") else ""))
            continue

        if line.startswith("/approvals"):
            if not active_id:
                print("No active opportunity. Use /new or /switch first.")
                continue
            record = opportunity_store.get(active_id)
            for a in record["approvals"]:
                print(f"  {a['approval_id']} [{a['status']}] {a['artifact_type']}: {a['summary']}")
            continue

        if line.startswith("/approve ") or line.startswith("/reject "):
            if not active_id:
                print("No active opportunity. Use /new or /switch first.")
                continue
            decision = "approve" if line.startswith("/approve ") else "reject"
            approval_id = line.split(" ", 1)[1].strip()
            try:
                result = decide_approval(
                    active_id, approval_id, decision, reviewer="cli-user",
                    opportunity_store=opportunity_store, conversation_store=conversation_store,
                )
                print(f"Approval {approval_id} -> {result['status']}.")
            except ValueError as exc:
                print(f"Error: {exc}")
            continue

        # Otherwise, treat as a chat message to the agent.
        if not active_id:
            print("No active opportunity. Use /new <client name> first.")
            continue

        reply = orchestrator.chat(active_id, line)
        print(f"\nCopilot: {reply}\n")


if __name__ == "__main__":
    main()
