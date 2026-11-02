---
name: networking
description: Run the outreach funnel in Notion. Log target companies/teams, queue the people to reach for each one, log touches as dated notes, run the 3-day chase, and say who is up next. Not for keep-warm contacts (use rolodex).
---

# Networking: outreach funnel (Targets → Log)

Two core jobs:
1. **Targets**: log the companies and teams the user wants to reach.
2. **People**: add the contacts for each target to the Log, in sequence, so it is always clear who to reach next.

Always on demand. **Never sends a message, email or invite.** Every write is shown as a draft first and happens only after the user says "proceed". One "proceed" can cover a batch. Answers to questions are not a "proceed": end every draft with "answer and say proceed".

## Data sources

Configure these once. Re-fetch a data source before writing if the schema may have changed. If the live schema differs from this file, follow the live schema, flag the difference, and never add columns to make it match.

- **Targets**: `<TARGETS_DATA_SOURCE_ID>`. See `docs/schema.md`.
- **Log**: `<LOG_DATA_SOURCE_ID>`. Notes hold the full history as dated lines.
- **Applications**: `<APPLICATIONS_DATA_SOURCE_ID>`. **Read only.** Summarise a matching application in the target's Notes.
- **People**: `<PEOPLE_DATA_SOURCE_ID>`. Read freely; the rolodex skill owns writes.

## A. New target

1. **Intake:** company and team, in the user's words. Always ask for Priority if not given.
2. **Match** an existing target first. If one exists, update it instead; if the match is unclear, ask.
3. **Name** it `"Company / Team"`. Team / Role keeps the user's exact wording.
4. **Application:** search Applications; if found, add a one-line summary to Notes.
5. **Page body:** create the seven headings (Why this target, Timing, Sequence, Angle per seniority, Messages, Scoreboard, Exit). Fill a heading only with stated facts or existing prep notes; otherwise leave it bare.
6. **Draft**, then stop until "proceed".

## B. Add people to a target

1. **Intake per person:** name, seniority, profile link, Sequence #, any condition ("only after a chat with X"). If no order is given, propose one: juniors first, warm links before cold, same seniority = same number. Seniors are usually gated on an earlier contact.
2. **Seniority mapping:** visiting analyst → Analyst; Head of X → Director/MD; headhunter → HR/Recruiter. If unsure, ask.
3. **Collision check** before creating anything: name match in the Log (link the existing row, never duplicate) and in People (ask: queue them anyway, or update via rolodex?). A similar name is not a match; say so in one line.
4. **Backdated history is normal.** Log past touches on their real dates.
5. **Draft**, then write after "proceed".

## B2. Standalone recruiters

No target, no Sequence #, Seniority HR/Recruiter, Status Pending Reach-Out. Notes: coverage plus when to contact. The contact date goes in **Next Action**, and the daily brief surfaces it.

## C. Log a touch

All history goes in Notes as `**YYYY-MM-DD:** ...` lines, including the channel.

| Event | Status | Last Reach Out | Notes line |
|---|---|---|---|
| Connection request sent | Pending LinkedIn Connection | **leave blank** (it would start a false chase) | "connection request sent" |
| Request accepted | Send the message! | unchanged | "connection accepted" |
| Message sent | Pending Response | that date | "first message sent on <channel>" |
| Follow-up sent | Pending Response, tick Follow-up Sent | that date | "follow-up sent on <channel>" |
| Reply, next step later | Pending Reach-Out; Next Action = agreed date | unchanged | "replied: <gist>; contact again <date>" |
| Reply, next step now | Send the message! | unchanged | "replied: <gist>" |
| Call or coffee held | Done | unchanged | "call held: <gist>"; then offer promotion to People |
| No reply at the Died check | Died (only after the user confirms) | unchanged | "marked Died: <reason>" |

- **One follow-up only.** If asked for a second, remind the user, then ask: mark Died, or keep waiting?
- **Strict sequences:** when #n's request goes out, set #n+1's Next Action to +2 days (or the gap the user chose).
- **Dates** in the user's time zone. If a date is unclear, ask.

## D. Who's due

Same sections as the daily brief: Chase, Died checks, Due dates, Up next, Pending requests (more than 14 days), Keep-warm. Each item gets a short draft in the user's voice. If a fact the message needs is missing, ask for it rather than guess it.

## Rules

- Ambiguous match → ask. Missing field → ask explicitly; don't assume and merely flag the assumption.
- Notes are append-only. Never rewrite the user's text.
- Adding a select option rewrites the whole list: re-fetch, include every existing option verbatim, check affected rows before and after.
- Never add, rename or delete columns, or delete/merge rows, without a separate explicit yes.
- Profile links may be read once each. No bulk crawling.
