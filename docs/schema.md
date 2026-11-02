# Schema

Three Notion databases, linked by relations. `crm/models.py` is the same schema as code.

```
Targets (1) ──< Log / Contacts (many) ──promote──> People (keep-warm)
```

## Targets: where you want to get in

| Property | Type | Notes |
|---|---|---|
| Company + Position | title | `"Company / Team"`, e.g. `Maersk / Corporate Development` |
| Company | text | |
| Team / Role | text | in your own words |
| Priority | select | High · Medium · Low · Tried and Died |
| Status | select | Pending Reaching Out · In Progress · Done · Died |
| Notes | text | application status in one line, e.g. "Applied: X (online assessment submitted)" |
| Contacts | relation → Log | |

The **page body** holds the strategy, under seven fixed headings: *Why this target, Timing, Sequence, Angle per seniority, Messages, Scoreboard, Exit*. Headings are filled only with facts, never with filler.

## Log: one row per person in the funnel

| Property | Type | Notes |
|---|---|---|
| Name | title | carries the LinkedIn link |
| Company + Position | relation → Targets | empty for standalone recruiters |
| Seniority | select | Analyst · Associate · VP · Director/MD · HR/Recruiter |
| Sequence # | number | outreach order; **equal numbers run in parallel** |
| Status | select | see below |
| Last Reach Out | date | the last *message* (never a connection request) |
| Follow-up Sent | checkbox | one follow-up only |
| Follow-up Date | formula | `Last Reach Out + 3 days` |
| Next Action | date | an agreed or scheduled date ("talk again on the 8th") |
| Notes | text | append-only history, one dated line per event |

**Status values**

| Status | Meaning |
|---|---|
| Pending Reach-Out | queued, nothing sent |
| Send the message! | a message is due now |
| Pending LinkedIn Connection | request sent, waiting for an accept |
| Pending Response | message sent, chase clock running |
| Done | call/coffee held, or closed on a good note |
| Died | no reply after the one follow-up, or a dead end |

## People: relationships to keep warm

| Property | Type | Notes |
|---|---|---|
| Name | title | |
| Affiliations | multi-select | the person's **own** employer only, never a client or deal counterparty |
| Position / Profession | multi-select | only when an existing option genuinely fits |
| Conn. type | multi-select | Acquaintance, Work, Alumni, ... |
| Met? | status | In Person · Video Chat · Never |
| First met / Last Contact | date | |
| Reach Out Frequency | number (months) | `>= 99` means "don't nudge" |
| Next Follow-up | formula | `Last Contact + frequency` |

Page body: *Important Information* (dated notes), *Things this person likes*, *What to avoid*.
