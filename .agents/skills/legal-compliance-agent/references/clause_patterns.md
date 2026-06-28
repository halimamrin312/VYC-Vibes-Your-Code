# Clause Pattern Reference — Legal & Compliance Agent

Use this file when semantic search returns low-confidence results (< 0.6 similarity score).
Fall back to keyword/regex scanning of raw document text using these patterns.

---

## LQ-01 — Poison Pill / Change-of-Control
**Keywords:** "change of control", "change-of-control", "successor entity", "assignment without consent",
"termination upon merger", "anti-assignment", "acquirer consent required"

**Red-flag phrase patterns:**
- "shall terminate automatically upon ... acquisition"
- "requires prior written consent of [third party] in the event of ... merger"
- "rights are non-transferable and non-assignable"

---

## LQ-02 — Active Litigation
**Keywords:** "pending litigation", "arbitration proceeding", "claim filed", "lawsuit", "plaintiff",
"defendant", "injunction", "cease and desist", "court order"

**Red-flag phrase patterns:**
- "Company is currently a defendant in"
- "subject to a claim of"
- "regulatory investigation by"

---

## LQ-03 — IP Disputes
**Keywords:** "patent infringement", "trade secret misappropriation", "copyright dispute",
"IP ownership contested", "third-party IP claim", "license revocation", "open source obligation"

**Red-flag phrase patterns:**
- "Company does not solely own"
- "jointly developed with [third party]"
- "subject to GPL / AGPL license" (copyleft risk in SaaS acquisitions)

---

## LQ-04 — Indemnification
**Keywords:** "indemnify", "indemnification", "hold harmless", "defend and indemnify",
"uncapped indemnity", "consequential damages"

**Red-flag phrase patterns:**
- "unlimited indemnification obligation"
- "indemnify against all losses, damages, and expenses"
- "surviving indemnification obligations" (survive contract termination)

---

## LQ-05 — HR / Severance
**Keywords:** "severance", "golden parachute", "retention bonus", "change-of-control payment",
"acceleration of vesting", "double trigger", "single trigger"

**Red-flag phrase patterns:**
- "employee shall receive [X] months salary upon change of control"
- "all unvested options shall accelerate upon"
- "retention pool of $[amount]"

---

## LQ-06 — Non-Compete / Exclusivity
**Keywords:** "non-compete", "non-solicitation", "exclusivity", "right of first refusal",
"most favored nation", "exclusive supplier"

**Red-flag phrase patterns:**
- "shall not compete in [geography] for [X] years"
- "exclusive provider of [service] for the term"
- "right of first offer on any future acquisition"

---

## LQ-07 — Data Privacy / Regulatory
**Keywords:** "GDPR", "CCPA", "data breach", "personal data", "data processing agreement",
"regulatory fine", "compliance certification", "SOC 2", "HIPAA"

**Red-flag phrase patterns:**
- "subject to ongoing regulatory review"
- "data breach notification sent to"
- "fined [amount] for non-compliance with"

---

## LQ-08 — Revenue Guarantees / Earn-outs
**Keywords:** "earn-out", "revenue guarantee", "minimum purchase commitment", "take-or-pay",
"most favored nation pricing", "price protection"

**Red-flag phrase patterns:**
- "guaranteed minimum revenue of $[amount] per [period]"
- "failure to meet minimum results in penalty of"
- "earn-out payment contingent on [metric]"

---

## LQ-09 — Third-Party Consent / Deal Blockers
**Keywords:** "consent required", "prior written approval", "approval of lender",
"board approval required", "government approval", "regulatory clearance", "antitrust"

**Red-flag phrase patterns:**
- "transaction requires approval of [government body]"
- "lender consent required for any change of control"
- "customer consent required before assignment"

---

## LQ-10 — Auto-Renewal / Long Lock-ins
**Keywords:** "automatic renewal", "evergreen clause", "perpetual term", "termination notice period",
"minimum contract term", "early termination fee"

**Red-flag phrase patterns:**
- "renews automatically for successive [X]-year terms"
- "early termination fee of $[amount]"
- "notice of non-renewal must be provided [X] days prior"
