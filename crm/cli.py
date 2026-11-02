"""Command line: `python -m crm <command>`.

  brief    --date YYYY-MM-DD           print the daily brief for that day
  status   --target ID [--date]        sequence table + scoreboard for one target
  log      --contact ID --event EVENT  apply a funnel event and save
           [--move-on-days N]          with request_sent: schedule the next person N days later
  promote  --contact ID --as ID --affiliation X [--every MONTHS]
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from . import brief, rules
from .models import CLOSED
from .store import load_json, save_json

DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data" / "sample.json"


def _today(s: str | None) -> date:
    return date.fromisoformat(s) if s else date.today()


def cmd_brief(a) -> None:
    targets, contacts, people = load_json(a.data)
    day = _today(a.date)
    text = brief.render(targets, contacts, people, day)
    if text is None:
        print("Nothing due today: no calendar event would be created.")
        return
    print(brief.title(targets, contacts, people, day))
    print("-" * 60)
    print(text)


def cmd_status(a) -> None:
    targets, contacts, _ = load_json(a.data)
    t = next(x for x in targets if x.id == a.target)
    group = sorted((c for c in contacts if c.target_id == t.id), key=lambda c: (c.sequence or 99, c.name))
    print(f"{t.label}  [{t.priority.value}]")
    for c in group:
        lr = c.last_reach_out.isoformat() if c.last_reach_out else "-"
        print(f"  #{c.sequence or '-':<2} {c.name:<22} {c.seniority.value:<12} {c.status.value:<28} last {lr}")
    reached = sum(1 for c in group if c.last_reach_out)
    replied = sum(1 for c in group if any("repl" in n.text for n in c.notes))
    calls = sum(1 for c in group if c.status.value == "Done")
    print(f"  Scoreboard: reached {reached} · replied {replied} · calls {calls}")
    nxt = rules.up_next(group, _today(a.date))
    print("  Up next: " + (", ".join(c.name for c in nxt) if nxt else "nothing (waiting)"))
    open_ = [c for c in group if c.status not in CLOSED]
    if not open_:
        print("  Exit: every contact is closed. Consider marking the target Tried and Died.")


def cmd_log(a) -> None:
    targets, contacts, people = load_json(a.data)
    c = next(x for x in contacts if x.id == a.contact)
    day = _today(a.date)
    rules.log_touch(c, a.event, day, a.note or "",
                    date.fromisoformat(a.next_action) if a.next_action else None)
    siblings = [x for x in contacts if c.target_id and x.target_id == c.target_id]
    if a.event == "request_sent" and a.move_on_days:
        nxt = rules.schedule_move_on(siblings, c, day, a.move_on_days)
        if nxt:
            print(f"  move-on: {nxt.name} due {nxt.next_action.isoformat()}")
    if a.event == "accepted":
        nxt = rules.cancel_move_on(siblings, c, day)
        if nxt:
            print(f"  move-on cancelled for {nxt.name}")
    save_json(a.data, targets, contacts, people)
    print(f"{c.name}: {c.status.value} · last note: {c.notes[-1].render()}")


def cmd_promote(a) -> None:
    targets, contacts, people = load_json(a.data)
    c = next(x for x in contacts if x.id == a.contact)
    p = rules.promote(c, people, _today(a.date), a.as_id, a.affiliation, a.every)
    save_json(a.data, targets, contacts, people)
    print(f"{p.name} promoted to People as {p.id} (every {p.frequency_months or '-'} months)")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="crm", description="Outreach funnel CRM")
    p.add_argument("--data", default=str(DEFAULT_DATA), help="path to the JSON store")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("brief"); b.add_argument("--date"); b.set_defaults(fn=cmd_brief)
    s = sub.add_parser("status"); s.add_argument("--target", required=True); s.add_argument("--date")
    s.set_defaults(fn=cmd_status)
    lg = sub.add_parser("log")
    lg.add_argument("--contact", required=True)
    lg.add_argument("--event", required=True, choices=sorted(rules.TRANSITIONS))
    lg.add_argument("--date"); lg.add_argument("--note"); lg.add_argument("--next-action")
    lg.add_argument("--move-on-days", type=int)
    lg.set_defaults(fn=cmd_log)
    pr = sub.add_parser("promote")
    pr.add_argument("--contact", required=True); pr.add_argument("--as", dest="as_id", required=True)
    pr.add_argument("--affiliation", required=True); pr.add_argument("--every", type=int)
    pr.add_argument("--date"); pr.set_defaults(fn=cmd_promote)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
