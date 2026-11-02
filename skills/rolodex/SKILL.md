---
name: rolodex
description: Add or update one contact in the People database (keep-warm relationships) from raw material the user supplies, such as notes, an email, a screenshot or a profile link.
---

# Rolodex: People database add/update

Always **on demand and single-person**. Never scheduled, never in the background, never more than one contact per run unless the user asks for a batch.

## Data source

- People data source: `<PEOPLE_DATA_SOURCE_ID>` (see `docs/schema.md`)
- Templates: Professional, Personal. **The user picks the template; never infer it.**

## Workflow

1. **Intake:** raw material about one person, plus the template for a new contact.
2. **Enrich from a supplied link** with a single read of that one profile. If it's login-walled, say so instead of guessing.
3. **Match** on name, email and affiliation. No match → new page. Match → diff. Ambiguous → show candidates and ask.
4. **Draft**, following these rules:
   - **Affiliations = the person's own employer only.** Clients, counterparties and deal names go into notes.
   - Any missing or ambiguous field → ask explicitly (which date, work or private phone, frequency units).
   - A new option value (e.g. a new company) → ask first, unless the user stated the exact value.
   - **Never create a new property** without an explicit yes.
   - Reach Out Frequency is the user's call; ask if it's relevant and not supplied.
   - Position only if an existing value genuinely fits; otherwise leave it blank.
5. **Notes are a dated log.** Every new fact is appended as `**YYYY-MM-DD:** ...`. Never overwrite; updates append after the last existing line.
6. **New-page layout** mirrors the template: two columns. *Important Information* holds the dated notes; *Things this person likes* and *What to avoid* stay empty unless the user supplied that detail.
7. **Show the full draft and stop.** New page: property table plus notes. Update: field-by-field diff plus the new notes entry. Write only after "proceed".

## Out of scope

Background digests, calendar or email auto-pull, bulk profile scraping, and writing anything without an explicit "proceed".
