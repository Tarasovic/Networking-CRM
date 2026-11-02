"""Storage: a JSON file for the demo, and an optional read-only Notion adapter.

The JSON layout is the same shape as the three Notion databases, so the demo
and the live system run through identical rules.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from .models import Contact, Note, Person, Priority, Seniority, Status, Target


def _d(v: Any):
    return date.fromisoformat(v) if v else None


def _notes(raw):
    return [Note(date.fromisoformat(n["on"]), n["text"]) for n in raw or []]


def load_json(path: str | Path) -> tuple[list[Target], list[Contact], list[Person]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    targets = [Target(t["id"], t["company"], t["team"], Priority(t["priority"]), t.get("notes", ""))
               for t in data["targets"]]
    contacts = [
        Contact(
            id=c["id"], name=c["name"], seniority=Seniority(c["seniority"]), status=Status(c["status"]),
            target_id=c.get("target_id"), sequence=c.get("sequence"),
            last_reach_out=_d(c.get("last_reach_out")), follow_up_sent=c.get("follow_up_sent", False),
            next_action=_d(c.get("next_action")), request_sent=_d(c.get("request_sent")),
            after=c.get("after"), move_on_from=c.get("move_on_from"), notes=_notes(c.get("notes")),
        )
        for c in data["contacts"]
    ]
    people = [
        Person(p["id"], p["name"], p["affiliation"], date.fromisoformat(p["last_contact"]),
               p.get("frequency_months"), p.get("met", "In Person"), _notes(p.get("notes")))
        for p in data.get("people", [])
    ]
    return targets, contacts, people


def save_json(path: str | Path, targets, contacts, people) -> None:
    def enc(o):
        if isinstance(o, date):
            return o.isoformat()
        if hasattr(o, "value"):
            return o.value
        raise TypeError(o)

    def note_list(ns):
        return [{"on": n.on.isoformat(), "text": n.text} for n in ns]

    out = {
        "targets": [asdict(t) for t in targets],
        "contacts": [{**asdict(c), "notes": note_list(c.notes)} for c in contacts],
        "people": [{**asdict(p), "notes": note_list(p.notes)} for p in people],
    }
    Path(path).write_text(json.dumps(out, indent=2, default=enc, ensure_ascii=False) + "\n", encoding="utf-8")


class NotionAdapter:
    """Minimal read-only loader for a live Notion workspace with the schema in docs/schema.md.

    Maps Targets and the core Log fields (status, sequence, dates, follow-up flag),
    which is enough for the chase, due-date and up-next sections. It does not map
    request dates, gates, note history or the People table, so stale requests,
    gating and keep-warm only run on the JSON store. Requires ``pip install
    notion-client`` plus NOTION_TOKEN, NOTION_TARGETS_DB and NOTION_LOG_DB.
    Not exercised by the test suite.
    """

    def __init__(self) -> None:
        from notion_client import Client  # optional dependency

        self.client = Client(auth=os.environ["NOTION_TOKEN"])
        self.targets_db = os.environ["NOTION_TARGETS_DB"]
        self.log_db = os.environ["NOTION_LOG_DB"]

    def _rows(self, db: str):
        cursor = None
        while True:
            res = self.client.databases.query(database_id=db, start_cursor=cursor) if cursor \
                else self.client.databases.query(database_id=db)
            yield from res["results"]
            if not res.get("has_more"):
                break
            cursor = res["next_cursor"]

    @staticmethod
    def _text(prop) -> str:
        items = prop.get("title") or prop.get("rich_text") or []
        return "".join(i["plain_text"] for i in items)

    @staticmethod
    def _sel(prop):
        s = prop.get("select") or prop.get("status")
        return s["name"] if s else None

    @staticmethod
    def _date(prop):
        d = prop.get("date")
        return date.fromisoformat(d["start"][:10]) if d else None

    def load(self):
        targets = []
        for r in self._rows(self.targets_db):
            p = r["properties"]
            targets.append(Target(r["id"], self._text(p["Company"]), self._text(p["Team / Role"]),
                                  Priority(self._sel(p["Priority"]) or "Medium"), self._text(p["Notes"])))
        contacts = []
        for r in self._rows(self.log_db):
            p = r["properties"]
            rel = p["Company + Position"]["relation"]
            contacts.append(Contact(
                id=r["id"], name=self._text(p["Name"]),
                seniority=Seniority(self._sel(p["Seniority"]) or "Analyst"),
                status=Status(self._sel(p["Status"]) or "Pending Reach-Out"),
                target_id=rel[0]["id"] if rel else None,
                sequence=p["Sequence #"].get("number"),
                last_reach_out=self._date(p["Last Reach Out"]),
                follow_up_sent=p["Follow-up Sent"]["checkbox"],
                next_action=self._date(p["Next Action"]),
            ))
        return targets, contacts, []
