"""The daily brief: one plain-text digest of what needs doing today.

In the live system this text becomes the description of a single 15-minute
calendar event each morning, so it is deliberately plain text (calendar apps
show HTML literally). An LLM adds a draft message under each item; this
module produces the deterministic part: what is due and why.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from . import rules
from .models import CLOSED, Contact, Person, Target

MAX_ITEMS = 10
SECTIONS = ("CHASE", "DIED CHECKS", "DUE DATES", "UP NEXT", "PENDING REQUESTS", "KEEP-WARM")


@dataclass
class Item:
    section: str
    title: str
    why: str
    do: str


def _who(c: Contact, targets: dict[str, Target]) -> str:
    where = targets[c.target_id].label if c.target_id else "Recruiter"
    return f"{c.name} · {where}"


def collect(targets: list[Target], contacts: list[Contact], people: list[Person],
            today: date) -> tuple[list[Item], list[str]]:
    t = {x.id: x for x in targets}
    items: list[Item] = []

    for ci in rules.chase(contacts, today):
        c = ci.contact
        last = c.last_reach_out.isoformat()
        if ci.kind == "follow-up":
            when = "due today" if ci.overdue_days == 0 else f"{ci.overdue_days}d past the 3-day window"
            items.append(Item("CHASE", _who(c, t), f"No reply since {last} ({when}).",
                              "Send the one follow-up."))
        else:
            items.append(Item("DIED CHECKS", _who(c, t),
                              f"Follow-up sent {last}, still no reply.",
                              "Mark Died, or keep waiting."))

    for c in rules.due_dates(contacts, today):
        context = f" Last note: \"{c.notes[-1].text}\"." if c.notes else ""
        items.append(Item("DUE DATES", _who(c, t),
                          f"Agreed date {c.next_action.isoformat()} has arrived.{context}",
                          "Act on the agreed step, then log it."))

    by_target: dict[str, list[Contact]] = {}
    for c in contacts:
        if c.target_id:
            by_target.setdefault(c.target_id, []).append(c)
    rank = {"High": 0, "Medium": 1, "Low": 2, "Tried and Died": 3}
    for tid, group in sorted(by_target.items(), key=lambda kv: rank[t[kv[0]].priority.value]):
        for c in rules.up_next(group, today):
            if c.next_action and c.next_action <= today:
                continue  # already listed under DUE DATES
            items.append(Item("UP NEXT", _who(c, t),
                              f"#{c.sequence} is now open for {t[tid].label}.",
                              "Send the first message." if c.status.value == "Send the message!"
                              else "Send a connection request or first message."))

    for c in rules.stale_requests(contacts, today):
        age = (today - c.request_sent).days
        items.append(Item("PENDING REQUESTS", _who(c, t),
                          f"Connection request unanswered for {age} days.",
                          "Try email, move to the next person, or mark Died."))

    for p, nxt in rules.keep_warm(people, today):
        items.append(Item("KEEP-WARM", f"{p.name} · {p.affiliation}",
                          f"Check-in due {nxt.isoformat()} (every {p.frequency_months} months).",
                          "Send a short, no-ask update."))

    hygiene: list[str] = []
    if today.weekday() == 0:  # Mondays only
        empty = [x.label for x in targets
                 if x.priority.value != "Tried and Died"
                 and not any(c.target_id == x.id and c.status not in CLOSED for c in contacts)]
        if empty:
            hygiene.append("Targets with no open contacts: " + ", ".join(empty))
        noseq = [c.name for c in contacts if c.target_id and c.sequence is None and c.status not in CLOSED]
        if noseq:
            hygiene.append("Contacts missing a sequence number: " + ", ".join(noseq))
        broken = [c.name for c in rules.broken_gates(contacts)]
        if broken:
            hygiene.append("Gated on an unknown contact (would never open): " + ", ".join(broken))
    order = {s: i for i, s in enumerate(SECTIONS)}
    items.sort(key=lambda it: order[it.section])  # stable: keeps within-section order
    return items, hygiene


def render(targets: list[Target], contacts: list[Contact], people: list[Person],
           today: date) -> Optional[str]:
    """Return the brief, or None on an empty day (no event is created)."""
    items, hygiene = collect(targets, contacts, people, today)
    if not items and not hygiene:
        return None

    shown, overflow = items[:MAX_ITEMS], items[MAX_ITEMS:]
    lines = [f"Daily networking brief · {today.strftime('%a %d %b %Y')}", ""]
    section, n = None, 0
    for it in shown:
        if it.section != section:
            section = it.section
            lines += [section, ""]
        n += 1
        lines += [f"{n}. {it.title}", f"Why: {it.why}", f"Do: {it.do}", ""]

    if overflow:
        by_sec: dict[str, list[str]] = {}
        for it in overflow:
            by_sec.setdefault(it.section.lower(), []).append(it.title.split(" · ")[0])
        for sec, names in by_sec.items():
            lines.append(f"+{len(names)} more {sec}: {', '.join(names)}")
        lines.append("")

    if hygiene:
        lines += ["MONDAY HYGIENE", ""] + [f"- {h}" for h in hygiene] + [""]

    empty = [s for s in SECTIONS if not any(i.section == s for i in items)]
    if empty:
        lines.append("Nothing in: " + ", ".join(s.lower() for s in empty) + ".")
    lines.append("Nothing sent or written. Every message goes out manually.")
    return "\n".join(lines)


def title(targets, contacts, people, today) -> str:
    """Calendar event title, e.g. 'Networking: 2 follow-ups, 1 up next'."""
    items, _ = collect(targets, contacts, people, today)
    counts: dict[str, int] = {}
    for i in items:
        counts[i.section] = counts.get(i.section, 0) + 1
    labels = {"CHASE": ("follow-up", "follow-ups"), "DIED CHECKS": ("died check", "died checks"),
              "DUE DATES": ("due date", "due dates"), "UP NEXT": ("up next", "up next"),
              "PENDING REQUESTS": ("stale request", "stale requests"),
              "KEEP-WARM": ("keep-warm", "keep-warm")}
    parts = [f"{v} {labels[k][v != 1]}" for k, v in counts.items()]
    return "Networking: " + (", ".join(parts) if parts else "nothing due")
