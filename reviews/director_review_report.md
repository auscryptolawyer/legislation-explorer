# Director Review Report

**Advice:** 6.10 — Division 152 Small Business CGT Concession Cascade (draft variant memo, internal, created 2 July 2026)
**Reviewed:** 1 August 2026
**Continuation completed:** 1 August 2026 (verification round run against live Cadena MCP)
**Reviewer:** Cadena Director Review (AI-assisted)

**Verification source:** Cadena MCP V2.7.2. All ITAA 1997 provisions checked against Compilation 263, last updated 1 April 2026.

> **Status of this document.** This is the updated report. The first pass (1 August 2026) left a block of citations "not verified this session" and flagged several items for confirmation. This continuation closed those gaps against the live Cadena MCP: the s 328-440 material gap, the load-bearing logic sections (s 152-115, s 152-45, s 152-125), the outstanding case law (BBlood appeals, Minerva, Eichmann, PepsiCo, Mylan), and the TR 2022/4 date anomaly are now all verified.
>
> **Correction (post-review, 1 August 2026).** One first-pass finding was **overturned on closer reading of s 152-115(3) against s 152-110(1)(c)**: the §3.1 conclusion that the 328-G reset preserves *both* the 15-year and the significant-individual clocks was too strong. s 152-115(3) deems the transferee's **acquisition date** back to the transferor's — preserving the *continuous-ownership* limb, s 152-110(1)(b) — but it does **not** carry the transferor's *significant-individual history* to the transferee for the purposes of s 152-110(1)(c). A restructure into a fresh entity can therefore still fail the 15-year exemption on the SI limb. The instruction to "invert Common Blocker 5 and delete 'model both before choosing'" is withdrawn. See the rewritten §3.1 and §6. Every other first-pass finding was confirmed. Items that remain genuinely open (Obsidian playbook novelty, Part IVA, ATO QCs) are listed under Scope.

**Scope limitations:**
- Part IVA analysis excluded at the reviewer's direction. Flagged only where a provision or authority is misdescribed. (PepsiCo [2025] HCA 30 is now confirmed on the record — see §1.2 — but the Part IVA merits remain out of scope.)
- No Obsidian connector available this session (unchanged). Step 6 alternative strategies proceed without playbook context. **Novelty relative to existing playbook entries remains unconfirmed.**
- ATO QC references deprioritised by the reviewer and not verified (unchanged).
- Converted-advice appendix omitted as unnecessary.

---

## 1. Citation Verification

### 1.1 Legislation (ITAA 1997 unless stated)

| Provision | Status | Notes |
|---|---|---|
| s 152-10 | Verified | Basic conditions accurate as described, including the s 152-10(4) carve-outs for J2, J5, J6. Memo omits the partnership limb in (1)(c)(iii). |
| s 152-15 | Verified | $6,000,000, "just before the CGT event". Accurate. |
| s 152-20 | Verified | See §3.2. Memo's characterisation of the levers is partly wrong. |
| s 152-35 | Verified | Half of the ownership period, or 7½ years where owned more than 15 years. Accurate. |
| s 152-40 | Verified | Pulled to test the s 152-10(2A) point. See §2. |
| s 152-45 | **Verified (this session)** | Continuing-time-period rule for the **active asset test**. Confined to Subdiv 124-B, FSR transition, and Subdiv 126-A (marriage breakdown) rollovers. **It does not apply to a 328-G restructure.** See §3.1 and §6. |
| s 152-55 | Verified | Significant individual is 20% SBPP. |
| s 152-60 | Verified | Stakeholder is an SI, or a spouse of an SI with SBPP above zero. |
| s 152-65 | Verified | SBPP is direct plus indirect. Load-bearing. See §3.4. |
| s 152-70 | Verified | Direct SBPP table. Item 3 (discretionary trust) runs on actual distributions in the relevant year. |
| s 152-75 | Verified | Indirect SBPP computed multiplicatively through interposed entities. Load-bearing. |
| s 152-105 | Not verified | Individual 15-year exemption. Cross-referenced throughout s 152-115; not independently pulled. Low materiality for the cascade (company/trust route governs). |
| s 152-110 | Verified | All four conditions accurate as stated. Memo omits s 152-110(3). |
| s 152-115 | **Verified (this session) — memo half-right** | s 152-115(3) deems the transferee's **acquisition date** back to the transferor's on a 328-450/328-455 transfer, preserving the continuous-ownership limb s 152-110(1)(b). It does **not** carry the significant-individual history for s 152-110(1)(c). See rewritten §3.1. |
| s 152-125 | **Verified (this session)** | Cap in (2) and both limbs, the later-of window in (1)(b), the (4) extension, the (3) not-a-dividend/not-frankable mechanic, and the (1)(a)(iv) Division 149 opportunity all confirmed verbatim. See §3.3, §3.5, §3.8. |
| s 152-305 | **Verified (this session)** | Retirement exemption (Strategy 5 fallback). Under-55 individual must contribute the exempt amount to super (1)(b); company/trust needs the significant individual test + s 152-325 conditions. Lifetime cap sits in s 152-320 (not pulled). |
| s 152-410 | Verified | Accurate. |
| s 152-420 | **Miscited** | Memo cites it as the replacement asset period provision. It is "Rules where an individual who has obtained a roll-over dies". **Correct provision is s 104-190** (confirmed this session — see below). |
| s 104-185 | Verified | J2. Not cited in the memo's step 5 where it is the principal exposure. |
| s 104-190 | **Verified (this session)** | The replacement asset period provision. Later of 2 years / 6 months post-earnout; (2) Commissioner extension. This is the provision the memo should have cited instead of s 152-420. |
| s 104-197 | **Verified (this session)** | CGT event J5. Fires at the **end** of the replacement asset period on failure to acquire/qualify a replacement. (5) confirms the period is set by s 104-190. See §3.6. |
| s 149-30 | Verified | (1A) deems fresh acquisition. Relevant to Common Blocker 4. |
| s 328-430 | Verified | Six conditions confirmed. |
| s 328-440 | **Verified (this session) — material gap confirmed** | Ultimate economic ownership for discretionary trusts. Requires (a) a non-fixed **family trust** before and after, and (b)/(c) every individual with ultimate economic ownership before and after is a member of the **family group** (Sch 2F ITAA 1936). Confirms the first pass's prediction. The memo never mentions it. See §6. |
| s 328-450 | **Verified (this session)** | "Transfers not to affect income tax positions… except as provided by this Subdivision." Confirms Subdiv 328-G has **no general acquisition-time deeming**. See §2. |
| s 328-455 | **Miscited** | Memo says it "deems the transferee to acquire at roll time". It is a cost rule only, headed "Effect of small business restructures on transferred cost of assets". |
| s 328-475 | Verified | Targeted carryover for the J2/J5/J6 choice only. |
| s 115-215 | Verified | Discount preservation sits here, not in s 115-228. |
| s 115-228 | Verified | Specific entitlement formula. Two-month recording deadline in (1)(c). |

**Still not verified this session (lower materiality):** s 328-435, s 328-445, s 328-460, s 328-465, s 328-470, s 104-198 (J6), s 115-5, s 115-10, s 115-225, s 152-320 (retirement lifetime cap), Part IVA (ss 177A, 177C, 177D, 177F), s 100A ITAA 1936. The first-pass **material** gap (s 328-440) is now closed; s 104-198 (J6) is the only remaining CGT-event section the memo relies on that was not independently pulled, and it pairs with J5 (s 104-197, now verified) on the same failure-of-replacement footing.

### 1.2 Cases

| Citation | Status | Notes |
|---|---|---|
| Eichmann [2020] FCAFC 155 | **Verified (this session), style corrected** | Confirmed: case name is *Eichmann v Commissioner of Taxation*, taxpayer as appellant, **appeal allowed**. On appeal from *Commissioner of Taxation v Eichmann* [2019] FCA 2155, which went the other way. Active-asset construction (s 152-40(1)(a): no "direct functional relevance"; question of fact and degree; construed beneficially) confirmed — supports Strategy 2. |
| Mylan [2024] FCA 253 | **Unverified holding — CDN-0038 live** | Reconfirmed this session: `get_case("[2024] FCA 253")` still returns "Case not found"; `search_cases`/`search_all` return the record with a **summary but an empty `case_name`**, and the `did_you_mean` fallback still misdirects to Master Tax Guide commentary ("What was the dominant purpose?"). Correct name is *Mylan Australia Holding Pty Ltd v Commissioner of Taxation (No 2)*; [2023] FCA 672 is Mylan No 1. Memo's bare "Mylan" is ambiguous across the two. **Holding still not verifiable through the canonical lookup path.** |
| Minerva [2024] FCAFC 28 | **Verified (this session)** | *Minerva Financial Group Pty Ltd v Commissioner of Taxation*, **appeal allowed**. The "but for" holding is confirmed verbatim: the primary judge erred by treating the absence of a commercial explanation as indicative of tax purpose, "effectively applying a 'but for' test". See §2. |
| Guardian AIT [2023] FCAFC 3 | Exists, misfiled | Listed under "(s 100A)" only. It is a split decision across two appeals and the Part IVA half is substantial. (Cited by both Minerva and PepsiCo — see §2.) |
| BBlood [2022] FCA 1112 | **Superseded — appeals now verified** | First instance only in the memo. The substantive Full Court decision is **[2023] FCAFC 89** (*B&F Investments Pty Ltd atf Illuka Park Trust v Commissioner of Taxation*): s 100A applied, IP Trustee's appeal dismissed, BE Co's appeal allowed on the alternative-assessment point. **[2023] FCAFC 114** (*Bblood Enterprises Pty Ltd v Commissioner of Taxation*) is the **costs judgment only** (Commissioner to pay 20% of costs). See §6 — cite FCAFC 89 for the s 100A holding, not both interchangeably. |
| PepsiCo [2025] HCA 30 | **Verified (this session)** | *Commissioner of Taxation v PepsiCo Inc; … v Stokely-Van Camp, Inc*, 13 August 2025. Royalty WHT (no) and diverted profits tax (yes). Current apex Part IVA/DPT authority; cites Guardian AIT and Hart. Relevant to the memo's currency, not to the domestic cascade merits. |

### 1.3 Rulings and Guidelines

| Reference | Status | Notes |
|---|---|---|
| LCR 2016/3 | Verified | Final. Genuine restructure guidance for Subdiv 328-G. |
| TR 2022/4 | **Verified (this session); date anomaly confirmed** | Final. The record carries `date_of_effect: 2023-09-27`, exactly as flagged — anomalous for a 2022 ruling and likely an addendum/consolidation artifact. **Do not rely on the recorded date** as the original date of effect. Substantive content confirms the "purpose of *any party*" low bar (see §2). |
| PCG 2022/2 | Verified | Final, effect 2022-01-01. White, green, red zone framework. See alignment note at §2. |
| ATO QC 22667 | Not verified | Deprioritised (unchanged). |
| ATO QC 52286 / 52288 | Not verified | Deprioritised (unchanged). |

---

## 2. Source-to-Argument Alignment

- **s 328-455 (step 3 mechanic)** — Does not support. The section fixes the transfer amount at roll-over cost. It contains no acquisition-time deeming. The step 3 outcome is nonetheless correct, but on different reasoning: Subdiv 328-G has no general deeming (**confirmed this session via s 328-450**, which is a "no direct consequences except as provided" rule), and the targeted carryovers that do exist (s 152-115(3), s 328-475, s 328-460) are each expressly confined. The absence of s 152-35 from those lists is the argument for the fresh clock.

- **s 152-115 (Common Blocker 5)** — Partly contradicts, partly confirms the memo (corrected). s 152-115(3) provides that where s 328-450 or s 328-455 applies to a transfer to you, paras 152-105(b), (c) and 152-110(1)(b), (c) apply as if you acquired the asset when the transferor did. That deems the **acquisition date** only, which preserves the continuous-ownership limb (1)(b). It does **not** attribute the transferor's significant-individual history to the transferee, so the SI limb (1)(c) can still fail. The blocker's bottom line (a reset can cost the 15-year exemption) is defensible; its stated mechanism ("breaks continuous ownership") is wrong — the exposure is (1)(c), not (1)(b). See rewritten §3.1.

- **s 152-125 (step 7)** — Partially supports. The disregard is real but capped under (2), and the memo states neither the cap nor its two limbs. Cap arithmetic confirmed verbatim this session (see §3.3).

- **s 115-228 (step 7 discount preservation)** — Does not support the proposition attached. s 115-228 is the specific entitlement formula. Discount preservation is in s 115-215(4)(a), which applies the discount only "if you are the kind of entity that can have a discount capital gain".

- **Minerva [2024] FCAFC 28** — Partially supports, and now verified. The "ordinary business or family dealings" framing is defensible through the Part IVA EM and Hart. The sharper holding, and the better cite, is that the primary judge erred by treating the absence of a commercial explanation as indicative of tax purpose, which the Full Court characterised as effectively a "but for" test. **Currency note:** Minerva is now cited by three 2025 Full Court decisions — *Ziegler v Commissioner of Taxation* [2025] FCAFC 168, *Commissioner of Taxation v Hicks* [2025] FCAFC 171, and *Merchant v Commissioner of Taxation* [2025] FCAFC 56 — and by the High Court in PepsiCo [2025] HCA 30.

- **Guardian AIT [2023] FCAFC 3** — Supports on s 100A. Consensus and adoption required; mere expectation that an arrangement could be reached later is insufficient. The Court also separated Part IVA attribution of purpose from s 100A's requirement of an actual agreement.

- **PCG 2022/2 (s 100A mitigation)** — Does not support as used. The memo lists "green-zone" as a mitigation for s 100A risk. The Guideline states in terms that it does not replace the Commissioner's interpretation of the law in TR 2022/4. Green zone means the Commissioner will not allocate compliance resources. It does not affect liability. The risk table conflates audit likelihood with legal exposure.

- **TR 2022/4** — Supports, but the memo understates it. **Confirmed this session:** the tax reduction purpose limb is satisfied if a purpose of *any party* is tax reduction. That is a low bar, so the ordinary dealing exception does all the work. The memo's "keep distributions genuine and paid" maps onto the exception without naming it.

---

## 3. Logical and Structural Review

### 3.1 The clocks: one carries over, one does not — corrected

The memo raises a conflict between step 3 and step 6 twice, in Common Blocker 5 and in Notes for Implementation, and instructs the adviser to "model both before choosing". My first pass called this a non-issue. That was wrong. There are three clocks, and they behave differently.

**Clock 1 — general/discount and active-asset ownership period: fresh (does not carry over).** Subdiv 328-G has no general acquisition-time deeming (s 328-450 confirmed), and s 152-45 — the active-asset-test continuing-time rule — does not extend to 328-G (it is confined to Subdiv 124-B, FSR transition, and Subdiv 126-A). The Master Tax Guide (¶12-380) puts it beyond doubt: "for the purpose of determining whether there will be a discount capital gain in the future, the transferee will be treated as having acquired the CGT asset at the time of the transfer. **Unlike other roll-overs, there is no deemed acquisition back to the date of original acquisition by the transferor.**" So the active-asset ownership period restarts — which is what step 3 wants.

**Clock 2 — 15-year continuous ownership, s 152-110(1)(b): carries over.** s 152-115(3) deems the transferee to have acquired the asset when the transferor acquired it. The continuous-ownership requirement is satisfied as if the transferee had held the asset from the transferor's original acquisition. This limb is protected.

**Clock 3 — 15-year significant-individual history, s 152-110(1)(c): does NOT carry over. This is the trap.** s 152-110(1)(c) requires that *the entity* had a significant individual for a total of at least 15 years *during which the entity owned the CGT asset*. s 152-115(3) deems only the **acquisition time**; it does **not** attribute the transferor's significant-individual history to the transferee. A transferee entity created (or first holding the asset) at the restructure has no significant-individual history for the deemed pre-transfer period, and no provision supplies one. So a 328-G restructure into a fresh entity can satisfy (1)(b) yet still **fail (1)(c)**, defeating the 15-year exemption.

**Net.** The step 3 reset and the step 6 exemption do not straightforwardly co-exist. The continuous-ownership limb is safe; the significant-individual limb is the live exposure. **Common Blocker 5's caution to "model both before choosing" stands and should not be deleted** — the first pass's instruction to invert and delete it is withdrawn.

**Corrections to the memo's wording, not its caution:**
- The memo attributes the risk to the reset "break[ing] continuous ownership." That is the wrong mechanism — s 152-115(3) protects continuous ownership. Reframe the blocker around **s 152-110(1)(c)**: the significant-individual history does not travel to the new entity.
- The memo cites "s 152-115 / s 152-45" as the rules to check. s 152-45 is inapposite (124-B/FSR/126-A only, and about the active asset test, not the 15-year exemption). Replace it with **s 152-110(1)(c) read with s 152-115(3)**.
- Practical consequence for the cascade: where the 15-year exemption is the target (step 5/6), a restructure into a **new** entity is hazardous. Prefer a route that keeps the significant-individual history intact — e.g. establish the qualifying SI history in the entity that will ultimately sell, well before any restructure, or avoid the fresh-entity reset where the 15-year exemption is being relied on.

### 3.1A The significant-individual requirement is a cost of the *structure*, not the exemption

The entire SI apparatus — step 4's "manufacture the significant individual across the required period," the s 152-110(1)(c) 15-year history, and the 328-G history trap in §3.1 — exists **only because the memo runs the asset through a company or trust**. Verified against s 152-105, s 152-110 and Master Tax Guide ¶7-165:

- **Individual owning the active asset directly** — s 152-105. The 15-year-SI condition in s 152-105(c) applies *only "if the CGT asset is a share in a company or an interest in a trust."* A direct asset owner needs **no significant individual at all**: basic conditions + 15 years' continuous ownership + 55/retiring (or permanently incapacitated). Step 4 is unnecessary and the 328-G (1)(c) trap never arises.
- **Company or trust owning the asset** — s 152-110. Needs a significant individual for periods **totalling at least 15 years** ((1)(c); not continuous, not the same person), plus an SI just before the event who is 55/retiring ((1)(d)).
- **Individual owning shares/units in the trading company/trust** — s 152-105(c) reimposes the 15-year SI test on the underlying entity. No escape.

**On the "15 years" itself:** it is 15 years **in aggregate**, not continuous and not one person. Where the asset is owned **longer** than 15 years there is slack (any 15 of the ownership years, with SI-free years permitted); where owned for the **bare 15-year minimum** there is none. You cannot qualify on fewer than 15 aggregate years, and the history cannot be back-filled.

**Takeaway for the entry:** the cleanest path for a marginal vendor who can hold the active asset **personally** is direct individual ownership — it removes step 4, removes the 328-G SI trap, and leaves only the 15-year ownership + retirement conditions. The memo never draws the individual-vs-entity line; it should, at the front.

### 3.2 Step 2 levers are partly unavailable and partly wrong

1. **Individuals only.** s 152-20(2)(b) opens "if the entity is an individual". Where countable assets sit in a company or trust, personal-use conversion is unavailable. The client profile expressly covers both.
2. **"Solely" for personal use and enjoyment.** Not mainly. Any income-producing use defeats it. The memo's "genuine personal-use assets" is softer than the provision.
3. **Main residence** is carved out of (b)(i) and handled under (b)(ii), with an add-back under (2A) where the dwelling produced assessable income and the individual satisfied s 118-190(1)(c).
4. **"Pay down connected-entity liabilities" does not work.** Net value under s 152-20(1) is assets less liabilities *related to those assets*. Paying a related liability with cash drops both sides equally. Net neutral. It reduces net value only where the liability is unrelated, and connected-entity liabilities are the ones most likely to be related.
5. **s 152-20(2)(a) is unused.** Disregard shares, units or other interests (except debt) in a connected entity, but include liabilities related to them. Dropping the asset while retaining the liability reduces net value. Statutory, and absent from the memo.
6. **s 152-20(5) to (7) is unused.** See §4, Strategy 1.

### 3.3 Extraction under s 152-125 has two limbs and neither is stated — verified

s 152-125(2) caps the disregarded payment at the stakeholder's participation percentage multiplied by the exempt amount, where that percentage is:

- **limb (a)**, company or item 2 (fixed) trust: the stakeholder's SBPP just before the CGT event
- **limb (b)**, item 3 (discretionary) trust: 100 divided by the number of stakeholders

Confirmed verbatim this session. The memo states neither, and the headline promise of a gain "streamed tax-free to multiple beneficiaries" is not qualified by either.

Under limb (b) the aggregate is always 100%, so nothing strands, but allocation is locked at 100/n per stakeholder with no weighting available. Pay one stakeholder above their share and the excess falls outside the disregard.

Separately, the window in s 152-125(1)(b) is the **later of** two years after the CGT event and, for a disposal, six months after the last possible benefit under a look-through earnout right, with a Commissioner extension available under (4) (all confirmed). The memo says "within 2 years". Given the client profile is trade sale, PE buyout or IPO, earnouts are likely.

### 3.4 Structure decides whether the cascade works

This is the finding that should sit at the front of the entry.

Because SBPP is direct plus indirect (s 152-65) and indirect is computed through interposed entities (s 152-75), where a company is held through a discretionary trust each individual's SBPP in the company is their trust distribution percentage for the relevant year. Limb (a) caps therefore aggregate to 100% **and** the split is chosen by resolution.

Ranked:

| Structure | Aggregate extraction | Allocation |
|---|---|---|
| Company held via discretionary trust | 100% | Fully flexible by resolution |
| Discretionary trust holding asset directly | 100% | Locked at 100/n |
| Company, shares held directly by individuals | Sum of SBPPs, may be under 100% | Fixed by register; changing it is a real ownership change |

Only the third case strands value. The Client Profile currently lists "individual, or via discretionary trust / company" as though the three are interchangeable. They are not, and the difference decides whether step 7 delivers.

### 3.5 Step 4's caveat is overstated in one direction

The Risk Assessment row reads "Cannot be retrofitted for 15-year exemption; pattern must exist across the period." That conflates two requirements:

- **s 152-110(1)(c)** is entity-level: the entity must have had *a* significant individual for a total of 15 years, expressly not continuous and expressly not the same person. The historic pattern **is** required here, so the caveat is correct as to this limb.
- **s 152-125(1)(c)** is point-in-time: the individual must have been a stakeholder just before the CGT event, and nothing more. (Confirmed this session.)

So no individual recipient needs a personal 15-year record to share in the exempt amount, provided the entity's history is satisfied by whoever held it. Stakeholders can be added at the last relevant distribution.

**Timing trap:** the input to that is a full-year measure. Item 3 of the s 152-70(1) table runs on distributions during the relevant year; s 152-70(5) can push the relevant year back to the last year in which a distribution was actually made; and s 152-70(6) produces 0% where the trust had net income, no tax loss, and made no distribution. The year being measured is not always the year assumed.

### 3.6 Step 5 warns about the wrong CGT event — J5 mechanics verified

The memo says "Watch J5/J6 (s 104-197/198) if replacement fails". **s 104-197 (J5) confirmed this session:** J5 happens at the **end of the replacement asset period** if no replacement asset is acquired, or the replacement does not satisfy the s 104-197(2) conditions. That is an endpoint event.

Since step 5 is a holding pattern until the retirement condition matures, the live exposure across that period is **J2 under s 104-185**: it bites after the end of the replacement asset period if the replacement asset stops being active, becomes trading stock, or starts being used solely to produce exempt or NANE income, and for shares or units if the s 104-185(1)(c) stakeholder condition stops being satisfied. That is a multi-year obligation on a step described as simply buying time.

Add the s 104-185(8) safe harbour: J2 does not happen under (2)(a) for a share or interest that ceased to be active only because of market value movements in assets already held at acquisition.

### 3.7 Two deadlines of different magnitude

Where there is both an exempt amount and a residual streamed gain, two clocks run: s 152-125(1)(b) in years, and s 115-228(1)(c) requiring the financial benefit to be recorded, in its character as referable to the capital gain, within **two months after the end of the income year**. The Documentation section folds both into "relevant deadlines". Missing the second drops the beneficiary out of specific entitlement and back into proportionate assessment.

### 3.8 Housekeeping

- Step numbering does not reconcile: High-Level Solution runs 1 to 6, Detailed Steps runs 1 to 7, Related Strategies maps "6.9 → step 6" and "4.7 → step 7" against a list where the 15-year exemption is step 5.
- Related Strategies maps "6.7 Division 122-A Small Business Rollover" to step 5, but step 5 is Subdiv 152-E. Division 122-A is a different rollover. *Reviewer instructed to leave as is.*
- s 152-110(3): the NANE treatment in (2) does not extend to balancing adjustment events on depreciating assets under Div 40 or Div 328.
- s 152-110(1A) disregards s 149-30(1A) for paras (1)(b) and (c), and s 152-125(1)(a)(iv) covers equivalent ground for the exempt amount (**confirmed this session**). A Division 149 history is therefore not a blocker for the 15-year route; on commentary the gain is worked out on the original cost base rather than the deemed cost base, so the full accrued gain is exempt and distributable. **Common Blocker 4 should be recast from risk to opportunity.**
- "Bypassing Division 7A" should be restated as the actual mechanism in s 152-125(3) (**confirmed**): not a dividend, not a frankable distribution.
- Authorities currency: confirmed instances of stale or superseded citation in a document dated July 2026 (BBlood at first instance — supersede with [2023] FCAFC 89; the Part IVA line stopping at 2024 while the database records *Commissioner of Taxation v PepsiCo Inc* [2025] HCA 30 and three 2025 Full Court decisions citing Minerva — Ziegler, Hicks, Merchant).

---

## 4. Alternative and Supplementary Strategies

No Obsidian access this session, so playbook overlap is unconfirmed for all of the below.

### Strategy 1: Look-through earnout election for NAVT reduction
**Objective achieved:** same (clears the s 152-15 gate)
**Structure:**
1. Confirm the disposal involves a look-through earnout right in existence at the valuing time.
2. Make the choice under s 152-20(6): treat the market value of the relevant CGT assets as the first element of cost base, or nil, or the capital proceeds, according to which limb of (5) applies.
3. Under (7), treat the market value of the earnout right itself as nil.

**Key provisions:** s 152-20(5) to (7), s 112-36, s 116-120
**Key risks:** availability depends on the right meeting the look-through conditions; interacts with the extended s 152-125(1)(b)(ii) window.
**Playbook reference:** unconfirmed. Absent from this entry.

**This is the most valuable omission identified.** It is a statutory NAVT reduction requiring no restructure, available precisely in the trade sale and PE buyout deals in the stated client profile.

### Strategy 2: Test the active asset gate on Eichmann before restructuring
**Objective achieved:** same, by removing the need for step 3
**Structure:**
1. Apply s 152-40(1)(a) as construed in Eichmann: no requirement of direct functional relevance or that use be integral; a question of fact and degree; construed beneficially. (Construction confirmed this session.)
2. If the asset qualifies, the gate is not failing and no 328-G restructure is required.

**Key provisions:** s 152-40(1)(a), s 152-35
**Key risks:** none material. Costless to run first.
**Playbook reference:** unconfirmed. Eichmann appears in the memo only as a bare citation tag.

### Strategy 3: s 152-20(2)(a) connected-entity interest exclusion
**Objective achieved:** partial (NAVT reduction)
**Structure:**
1. Identify interests (except debt) in entities connected with the taxpayer or with an affiliate.
2. Disregard those interests under s 152-20(2)(a) while including liabilities related to them.

**Key provisions:** s 152-20(2)(a), s 152-78
**Key risks:** turns on the connected-with analysis.
**Playbook reference:** unconfirmed. Absent from step 2.

### Strategy 4: Interpose or use a discretionary trust in the ownership chain
**Objective achieved:** same, with better extraction
**Structure:**
1. Where the asset is held by a company, confirm whether the shares are held via a discretionary trust.
2. If so, SBPP flows through s 152-65 and s 152-75 from the trust distribution percentage, so limb (a) caps aggregate to 100% and allocation is set by resolution.
3. If not, weigh whether inserting a trust is achievable on a genuine basis well ahead of the event. `[Part IVA: review separately]`

**Key provisions:** s 152-65, s 152-75, s 152-70(1) item 3, s 152-125(2)(a)
**Key risks:** any restructure to insert a trust engages the Subdiv 328-G conditions and its own timing constraints — **including s 328-440 for a discretionary trust** (family trust election + family-group membership before and after; confirmed this session).
**Playbook reference:** unconfirmed.

### Strategy 5: 50% active asset reduction plus retirement exemption
Already flagged in the memo's Common Blockers as the fallback where the significant individual is not yet 55 or not retiring. s 152-305 confirmed this session (under-55 individuals must contribute the exempt amount to super; company/trust route needs the significant individual test + s 152-325). The lifetime cap in s 152-320 was not verified this session.

---

## 5. Summary and Recommended Actions

| Item | Priority | Action | Verification status (this session) |
|---|---|---|---|
| s 152-125(2) cap and its two limbs absent | High | Add to step 7. State the arithmetic for each limb. | ✅ Confirmed verbatim |
| Structure determines outcome (§3.4) | High | Move to Client Profile. Stop treating the three structures as interchangeable. | ✅ (s 152-65/75/70 chain) |
| Step 2 unavailable for non-individuals | High | Qualify the step. s 152-20(2)(b) is individuals only. | — |
| s 152-20(5) to (7) earnout election missing | High | Add as a step 2 lever. | — |
| Common Blocker 5 mislabels the 15-year risk | High | **Keep the "model both before choosing" caution.** Reframe around s 152-110(1)(c): s 152-115(3) preserves the acquisition date (continuous ownership) but the significant-individual history does not carry to a fresh transferee. Drop the inapposite s 152-45 reference. | ✅ Corrected — see §3.1 |
| SI-15-year requirement is a structure cost | High | Add the individual-vs-entity split at the front. Direct individual ownership (s 152-105) needs **no** significant individual; only the company/trust route (s 152-110) and shares/units (s 152-105(c)) do. Removes step 4 and the 328-G SI trap. | ✅ Verified — see §3.1A |
| BBlood cited at first instance | High | Replace with **[2023] FCAFC 89** for the s 100A holding. [2023] FCAFC 114 is the costs judgment only — cite only if costs are relevant. | ✅ Both confirmed |
| s 328-455 and s 152-420 miscited | Medium | Correct both. Replacement asset period is **s 104-190** via s 104-185. | ✅ s 104-190 confirmed |
| Step 5 warns on J5/J6, exposure is J2 | Medium | Rewrite to s 104-185, add the (8) safe harbour. | ✅ J5 (s 104-197) confirmed |
| s 115-228 cited for discount preservation | Medium | Correct to s 115-215(4)(a) and its entity qualifier. | — |
| s 152-125(1)(b) window understated | Medium | Restate as the later of the two limbs, plus (4) extension. | ✅ Confirmed |
| s 115-228(1)(c) two-month deadline absent | Medium | Add to Documentation, separately from the s 152-125 window. | — |
| PCG 2022/2 green zone used as a legal mitigation | Medium | Recast as audit-risk only. | — |
| Common Blocker 4 (Division 149) framed as risk | Medium | Recast as opportunity per s 152-110(1A) and s 152-125(1)(a)(iv). | ✅ (1)(a)(iv) confirmed |
| Step 4 caveat overstated for recipients | Medium | Split the entity-level 15-year limb from the point-in-time stakeholder limb. | ✅ s 152-125(1)(c) confirmed |
| Authorities currency | Medium | Full pass. Supersede BBlood; add PepsiCo [2025] HCA 30 and the 2025 Minerva line. | ✅ PepsiCo + 3 cases confirmed |
| s 328-440 unverified | Medium | Verify before any discretionary-trust matter runs step 3. | ✅ **Now verified — FTE + family group required** |
| TR 2022/4 date | Medium | Do not rely on the recorded 2023-09-27 date. | ✅ Anomaly confirmed |
| Step numbering does not reconcile | Low | Renumber. | — |
| Minerva proposition | Low | Add the "but for" holding as the primary cite. | ✅ Confirmed verbatim |
| Eichmann party names reversed | Low | Correct style. | ✅ Confirmed |
| Mylan cited as bare "Mylan" | Low | Cite as Mylan (No 2); holding remains unverified. | ⚠️ CDN-0038 live; holding unverifiable |
| s 152-110(3) omitted | Low | Add the depreciating asset exception. | — |
| "Bypassing Division 7A" | Low | Restate as s 152-125(3). | ✅ Confirmed |

---

## 6. Verification Continuation — what this round resolved

Run against the live Cadena MCP (V2.7.2, Compilation 263). The first pass's findings held on verification; the notes below record confirmations and the handful of refinements.

**Legislation gaps closed.**
- **s 328-440 (the one material gap).** Statutory text confirms the ultimate-economic-ownership condition for discretionary trusts: a non-fixed **family trust** before and after the transfer, and every individual with ultimate economic ownership before/after a member of the **family group** (Sch 2F ITAA 1936). This is the family-trust-election requirement the first pass predicted "on commentary" — now confirmed on the face of the provision. **Action stands: verify FTE status before any discretionary-trust matter runs step 3.**
- **s 152-115(3), s 152-45, s 152-125(2), s 328-450, s 104-190, s 104-197, s 152-305** — all pulled and confirmed. The §3.3 cap finding is verified against statute.
- **Correction to §3.1 (this supersedes the first pass).** On re-reading s 152-115(3) against s 152-110(1)(c) and the Master Tax Guide (¶12-380), the first-pass "no conflict, both clocks preserved" conclusion was wrong. s 152-115(3) deems the transferee's **acquisition date** back to the transferor's — preserving continuous ownership, s 152-110(1)(b) — but does **not** carry the transferor's **significant-individual history** to the transferee for s 152-110(1)(c). A 328-G restructure into a fresh entity can satisfy (1)(b) and still fail (1)(c). The general/discount and active-asset ownership clock is fresh (Master Tax Guide: "no deemed acquisition back to the date of original acquisition by the transferor"). **Common Blocker 5's "model both before choosing" caution therefore stands; the instruction to delete it is withdrawn.** The memo's error is mechanism-labelling ("breaks continuous ownership") not the underlying risk.
- **Refinement retained (§3.1):** the memo's "s 152-115 / s 152-45" pairing is imprecise — s 152-45 governs the active-asset test for 124-B/FSR/126-A rollovers only and is inapposite to a 328-G reset; replace it with s 152-110(1)(c) read with s 152-115(3).

**Case law resolved.**
- **BBlood appeals** — refinement to the first-pass recommendation. **[2023] FCAFC 89** (*B&F Investments*) is the **substantive** s 100A appeal and the correct replacement cite. **[2023] FCAFC 114** (*Bblood Enterprises*) is only the **costs** judgment (20% costs). Do not cite the two interchangeably for the s 100A holding.
- **Minerva [2024] FCAFC 28** — appeal allowed; the "but for" holding confirmed verbatim; now cited by three 2025 Full Court decisions (Ziegler [2025] FCAFC 168, Hicks [2025] FCAFC 171, Merchant [2025] FCAFC 56) and by PepsiCo [2025] HCA 30.
- **Eichmann [2020] FCAFC 155** — party style and outcome confirmed exactly as flagged; active-asset construction confirmed (supports Strategy 2).
- **PepsiCo [2025] HCA 30** — confirmed on the record (13 Aug 2025); supports the currency point.
- **Mylan [2024] FCA 253** — CDN-0038 reconfirmed live (see below). Holding remains unverifiable via the canonical path.

**Rulings.**
- **TR 2022/4** — the anomalous `date_of_effect: 2023-09-27` is confirmed present on the record. Treat the recorded date as unreliable; substantive "purpose of any party" content confirmed.

**Still open (not closable this session):**
- **Obsidian playbook novelty** — no connector available; Strategies 1–5 remain of unconfirmed novelty against the existing playbook.
- **Part IVA merits** — excluded at the reviewer's direction (PepsiCo now on the record for currency only).
- **ATO QCs** and the low-materiality sections listed in §1.1 — deprioritised / not independently pulled.

---

## Appendix: Database Defect Raised

**CDN-0038** — `get_case("[2024] FCA 253")` returns "Case not found" for a record that exists and carries a summary, retrievable via `search_all` / `search_cases`. Canonical entry reported with an empty `case_name`. Search index and exact-lookup path are out of sync. **Reconfirmed live this session** (1 August 2026): the miss persists, and the `did_you_mean` fallback still returns Master Tax Guide commentary ("What was the dominant purpose?") for a case-shaped citation, so a lookup miss reads as genuine absence.

The first of these is correctness-critical for any verification workflow that treats "Case not found" as authoritative — a director review that relied on `get_case` alone would wrongly record *Mylan (No 2)* as non-existent. The safe pattern, used in this review, is to fall back to `search_all` / `search_cases` on any `get_case` miss before concluding a citation is bad.

Two follow-ups previously noted on the ticket remain relevant: the `did_you_mean` misdirection (above), and that a `report_issue` resubmission returned the same ticket number under a different category with `duplicate_of: null`. Because of that duplicate-handling behaviour, **no new ticket was filed this session** to avoid corrupting CDN-0038's record; this report documents the reconfirmation instead.
