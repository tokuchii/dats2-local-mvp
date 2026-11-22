# Permission Request Draft

**Status:** DRAFT FOR OWNER REVIEW — NOT SENT
**Roadmap task:** Phase 0.6
**Purpose:** Ask UPV TTBDO and DOST-PCAARRD for guidance and written permission before DATS 2.0 links to AANR-TRACER or stores TRACER-derived results.

No email has been sent. No DATS submission data, personal data, or unpublished technology information is included.

---

## Cover letter

**To:** Technology Transfer and Business Development Office (TTBDO), University of the Philippines Visayas `<ttbdo.upvisayas@up.edu.ph>`
**Cc:** DOST-PCAARRD `[Office / Contact Name] <[email]>`
**From:** `[Doc Arnan Full Name]`, `[Position]`, `[Institution]`
**Date:** `[Date]`
**Subject:** Request for guidance and written permission to link DATS 2.0 to AANR-TRACER

Dear `[Sir/Madam]`,

### 1. Purpose

We maintain DATS 2.0, a human-reviewed registry of 133 Philippine digital agriculture systems at `https://dat.pandoy.online` (source: `https://github.com/tokuchii/dats2-local-mvp`). We would like to link eligible DATS records to AANR-TRACER so that a technology owner can move from discovering a system in DATS to assessing its readiness in TRACER.

### 2. What we propose for the first phase

- A plain text link or button on eligible DATS record pages that opens `https://aanr-tracer.com` in a new tab.
- A printable evidence sheet generated only from existing DATS fields, grouped under TRACER's five public assessment areas and clearly labelled **PROVISIONAL — not the official TRACER questionnaire**.
- No data transmitted to TRACER, no automated assessment, no scraping, and no calls to any TRACER API.
- No use of the TRACER name or logo beyond a plain-text link until you confirm what is permitted.

### 3. Why we are asking

TRACER belongs to DOST-PCAARRD and UP Visayas. We do not want to assume that linking, attribution, stored results, or derived fields are permitted. We would rather agree the boundaries in writing before building beyond a simple link.

### 4. Requests

a. Is a plain hyperlink from DATS to TRACER acceptable? Is there a preferred attribution or wording?
b. May DATS use the name "AANR-TRACER" in text? May it use the TRACER logo? We will treat the logo as requiring separate written permission.
c. Who should we coordinate with for technical and methodological questions?
d. For a later phase, may DATS store a reviewer-confirmed TRACER level, assessment date, assessor, status, and the report file path, with the report supplied by the innovator? What may be stored, for how long, and under what privacy terms?
e. Does TRACER provide any results export, API, or shared identifier that DATS could use with permission? If so, what are the terms?
f. TRACER's public privacy policy states that a submitted assessment summary goes to DOST-PCAARRD and that OpenAI processes the technology description. Please confirm this so we can set the correct data-handling rules. DATS will not send any record or evidence to TRACER without a separate written agreement.
g. Which level descriptions, technology types, and assessment-area names may we cite publicly? Are the detailed questions and scoring rules available only through the assessment itself?

### 5. No data shared with this letter

This request contains no DATS submission data, no personal data, and no unpublished technology information. It asks only for guidance and permission.

### 6. Next step

We would be glad to demonstrate the proposed link and evidence sheet at your convenience. We will not promote the link publicly until we have your reply and Doc Arnan's approval.

Sincerely,

`[Name]`
`[Position]`
`[Institution]`
`[Email]`
`[Telephone]`

---

## Annex A — Phase 1 scope and non-goals

In scope:

- Link-out from eligible DATS records.
- Printable provisional evidence sheet from existing DATS fields.
- Clear labelling that DATS classifies a system while TRACER measures readiness.

Out of scope:

- Sending data to TRACER.
- Reading or storing TRACER results automatically.
- Scraping, automating, or reverse-engineering TRACER.
- Using TRACER's logo or implying endorsement.

## Annex B — Proposed Phase 2 fields, only if permitted

- DATS stable ID (`dats2_id`)
- TRACER technology type
- TRACER level (1-9)
- Assessment date
- Assessor or assessing office
- Assessment status
- Report file reference
- Reviewer who recorded the result
- Audit event and timestamp

## Annex C — Variables for the owner

- `[Doc Arnan Full Name]`, `[Position]`, `[Institution]`
- `[DOST-PCAARRD Office / Contact Name]`, `[email]`
- `[Date]`
- Whether to send from Doc Arnan's address or an official DATS address
