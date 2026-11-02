# networking-crm

**A personal outreach CRM: a Notion schema, a status-driven funnel and an automated daily brief, run day to day with Claude.**

Built by **Ruslan Pushkar** to run a structured networking campaign: many target teams, many contacts, and the follow-ups that usually fall through the cracks. This repo rebuilds the system as runnable Python on a synthetic dataset, alongside the prompts ("skills") that operate the live version.

> All people, notes and dates in this repo are fictional. Company names are realistic placeholders only and have no connection to the author's actual outreach.

---

## The problem

Networking for a competitive industry is a pipeline problem:

- **Too many threads.** Each target team has 2–12 people, each at a different stage.
- **Timing matters.** Chasing on day 2 looks pushy; on day 10, you're forgotten.
- **Order matters.** You don't cold-message a VP while their analyst still has your unanswered request.
- **Nothing should go out automatically.** Every message has to be written and sent by a person.

## How it works

```
                ┌──────────────┐        ┌────────────────────┐        ┌──────────────┐
  you ────────> │   Targets    │ 1 ── * │  Log (contacts)    │ ─────> │    People    │
  (via Claude)  │ company/team │        │ status · sequence  │ promote│  keep-warm   │
                └──────────────┘        │ dates · notes      │        └──────────────┘
                                        └─────────┬──────────┘
                                                  │ read-only, every morning
                                                  ▼
                                   ┌──────────────────────────────┐
                                   │ Daily brief (1 calendar event)│
                                   │ chase · due · up next · ...   │
                                   └──────────────────────────────┘
```

1. **Capture.** Say "add Maersk / Corporate Development, priority High, these three analysts in this order". The `networking` skill drafts the target page and contact rows, checks for duplicates, and writes them after an explicit *proceed*.
2. **Log.** "Sent Lena the first message" becomes a status change plus a dated, append-only note.
3. **Brief.** Every morning a scheduled task reads the databases and puts one 15-minute event on the calendar listing exactly who to chase, what's due and who's up next. If nothing is due (and, on Mondays, there are no hygiene findings), no event is created.
4. **Promote.** After a call, the contact moves to the People database with a keep-warm frequency, so the relationship doesn't go cold.

The rules behind each step (3-day chase, one follow-up, sequencing, 14-day stale requests, keep-warm) are in [`docs/funnel-rules.md`](docs/funnel-rules.md). The reasoning behind them, including what didn't work, is in [`docs/design-decisions.md`](docs/design-decisions.md).

## Example output

```
$ python -m crm brief --date 2026-03-02
Networking: 2 follow-ups, 1 died check, 2 due dates, 2 up next, 1 stale request, 2 keep-warm
------------------------------------------------------------
Daily networking brief · Mon 02 Mar 2026

CHASE

1. Leo Fontaine · Siemens / Investor Relations
Why: No reply since 2026-02-25 (2d past the 3-day window).
Do: Send the one follow-up.

2. Lena Moreau · Spotify / Corporate Strategy
Why: No reply since 2026-02-26 (1d past the 3-day window).
Do: Send the one follow-up.

DIED CHECKS

3. Priya Raman · Airbus / Corporate Development
Why: Follow-up sent 2026-02-27, still no reply.
Do: Mark Died, or keep waiting.

DUE DATES

4. Samir Haddad · Maersk / Corporate Development
Why: Agreed date 2026-03-01 has arrived. Last note: "send a connection request if Chloé hasn't accepted within 2 days".
Do: Act on the agreed step, then log it.
...
MONDAY HYGIENE

- Targets with no open contacts: Airbus / Treasury
- Contacts missing a sequence number: Ruth Adler
```

In the live system, Claude adds a short draft message in the user's voice under each item, built only from facts already in the database.

```
$ python -m crm status --target t-maersk
Maersk / Corporate Development  [High]
  #1  Chloé Martin           Analyst      Pending LinkedIn Connection  last -
  #2  Samir Haddad           Analyst      Pending Reach-Out            last -
  #3  Erik Santos            Analyst      Pending Reach-Out            last -
  Scoreboard: reached 0 · replied 0 · calls 0
  Up next: nothing (waiting)
```

## Run it

Python 3.10+, no dependencies for the demo.

```bash
git clone https://github.com/<you>/networking-crm && cd networking-crm
python -m crm brief --date 2026-03-02                 # the daily brief on sample data
python -m crm status --target t-spotify               # one target's sequence + scoreboard

# write commands change the JSON, so try them on a copy
cp data/sample.json /tmp/demo.json
python -m crm --data /tmp/demo.json log --contact c01 --event follow_up_sent --date 2026-03-02
python -m crm --data /tmp/demo.json log --contact c06 --event request_sent --move-on-days 2 --date 2026-03-02
python -m crm --data /tmp/demo.json promote --contact c12 --as p04 --affiliation Philips --every 3 --date 2026-03-02

pip install pytest && python -m pytest -q             # rule tests
```

`crm.store.NotionAdapter` is a minimal read-only loader for a Notion workspace with the same schema (`pip install notion-client`; set `NOTION_TOKEN`, `NOTION_TARGETS_DB`, `NOTION_LOG_DB`). It maps targets and the core contact fields, which covers the chase and due-date sections. Request dates, gates and keep-warm aren't mapped, so stale requests, gated up-next and keep-warm run on the JSON store only. In the live system Claude reads Notion directly through its connector.

## Repo layout

```
crm/
  models.py   schema as code: Target, Contact, Person, Status, Seniority, Priority
  rules.py    the funnel: chase, sequencing, move-on, stale requests, keep-warm, promotion, event table
  brief.py    daily brief generator (plain text, 10-item cap, Monday hygiene)
  store.py    JSON store + optional read-only Notion adapter
  cli.py      brief / status / log / promote
data/sample.json   synthetic dataset (8 targets, 16 contacts, 3 people)
docs/              schema, funnel rules, design decisions
skills/            the Claude prompts that run the live system
tests/             rule tests
```

## Running it with Claude

The live system has no app of its own. It's Notion plus three prompts:

| Skill | Role |
|---|---|
| [`skills/networking`](skills/networking/SKILL.md) | Add targets and contacts, log touches, say who's up next. Drafts every write and waits for "proceed". |
| [`skills/rolodex`](skills/rolodex/SKILL.md) | One-person add/update for the keep-warm People database. |
| [`skills/daily-brief`](skills/daily-brief/SKILL.md) | The scheduled task prompt behind the morning calendar event. |

Two principles run through all three: **the human sends every message**, and **the model asks rather than guesses** when a fact is missing.

## License

MIT © 2026 Ruslan Pushkar
