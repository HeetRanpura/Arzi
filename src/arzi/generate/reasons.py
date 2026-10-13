"""Templated plain-English reasons for training targets, several wordings per rule outcome."""

from __future__ import annotations

import random

from arzi.rules import RuleResult
from arzi.schema import CaseFacts

# {m} months of cover, {wp} waiting period months, {h} stay hours, {lim}/{chg} room rent, {cond}, {excl}
TEMPLATES: dict[str, list[str]] = {
    "moratorium_completed": [
        "The policy had {m} months of continuous cover at admission. After 60 months the insurer cannot reject for non-disclosure unless it proves fraud, so this rejection looks wrong.",
        "Cover had run for {m} months, past the 60-month moratorium. Non-disclosure can no longer be used to refuse the claim, barring established fraud.",
        "With {m} months of unbroken cover the moratorium period is complete. The insurer may not contest the claim for non-disclosure of {cond}.",
        "The moratorium applies: {m} months of continuous cover is more than 60. A non-disclosure rejection is not allowed at this stage except for proven fraud.",
    ],
    "ped_was_disclosed": [
        "The policy schedule shows {cond} was declared in the proposal form, so the claim of non-disclosure does not hold.",
        "{cond} is listed as a declared pre-existing disease on the policy. The insurer cannot say it was hidden.",
        "The insurer says {cond} was not disclosed, but the schedule records it as declared. That contradiction is grounds to contest.",
        "Because {cond} appears among the diseases declared at proposal, the non-disclosure ground is not supported by the policy itself.",
    ],
    "condition_unrelated_to_claim": [
        "{cond} was not declared and cover is only {m} months old, but it has no medical link to the illness claimed for. Ask the insurer to justify the connection.",
        "The undeclared condition ({cond}) is unrelated to this hospitalisation. With {m} months of cover the rejection is not clearly wrong, but it is worth questioning.",
        "Non-disclosure of {cond} is not disputed by the documents, yet the claim is for an unrelated illness. The insurer should explain why that defeats the claim.",
        "Cover is {m} months old and {cond} was not declared. Since the claim is for something unrelated, ask for the medical basis before accepting the rejection.",
    ],
    "non_disclosure_stands": [
        "{cond} was not declared in the proposal form, it is related to the illness claimed for, and cover is only {m} months old, short of the 60-month moratorium. The rejection looks valid.",
        "The schedule shows no disease was declared, the claim is linked to {cond}, and the policy has {m} months of cover, under 60. On these facts the insurer is within its rights.",
        "With {m} months of continuous cover the moratorium does not apply, and the undeclared {cond} is connected to this claim. This rejection is likely to stand.",
        "Nothing in the documents helps here: {cond} was not disclosed, it relates to the claim, and {m} months is below the 60 needed for the moratorium.",
    ],
    "accident_no_initial_waiting": [
        "The hospitalisation followed an accident. The initial 30-day waiting period does not apply to accidents, so this rejection looks wrong.",
        "This was an accident claim and the insurer relied on the initial waiting period, which is waived for accidents.",
        "The initial waiting period cannot be used against an accidental injury. The letter itself records that this was an accident.",
        "Accidents are covered from day one. Applying the 30-day initial waiting period to an accident is grounds to contest.",
    ],
    "accident_exempt_in_wording": [
        "The treatment followed an accident and the policy wording says waiting periods do not apply to accidents, so the {wp}-month waiting period should not have been used.",
        "The policy exempts accident claims from waiting periods. Since this was an accident, the {wp}-month waiting period is not a valid ground.",
        "Only {m} months of cover had run, but the wording waives waiting periods for accidents and this claim arose from one.",
        "The insurer applied a {wp}-month waiting period to an accident claim although its own wording exempts accidents.",
    ],
    "waiting_period_served": [
        "The policy had {m} months of continuous cover at admission, which meets the {wp}-month waiting period. The rejection looks wrong.",
        "Continuous cover of {m} months, counting from first inception, is not less than the {wp}-month waiting period relied on.",
        "The waiting period of {wp} months was already complete: cover had run {m} months by the admission date.",
        "Counting from the date of first inception, including any ported cover, the insured had {m} months of cover against a {wp}-month waiting period.",
    ],
    "waiting_period_not_served": [
        "Only {m} months of continuous cover had run at admission, less than the {wp}-month waiting period. The rejection looks valid.",
        "The waiting period relied on is {wp} months and the policy was {m} months old at admission, so the waiting period was not complete.",
        "Cover began {m} months before admission. That is short of the {wp} months required, and nothing in the documents exempts this claim.",
        "With {m} months of cover against a {wp}-month waiting period, the insurer applied the waiting period correctly.",
    ],
    "exclusion_not_in_wording": [
        "The insurer cites an exclusion for {excl}, but the list of permanent exclusions in the policy does not contain it.",
        "The exclusion relied on ({excl}) does not appear in the policy wording provided. An exclusion that is not in the policy cannot be applied.",
        "The policy lists its permanent exclusions and {excl} is not among them, so the ground of rejection is unsupported.",
        "Nothing in the policy's exclusion list covers {excl}. The rejection rests on an exclusion the policy does not have.",
    ],
    "exclusion_in_wording": [
        "The exclusion for {excl} is in the policy's list of permanent exclusions, so the rejection looks valid.",
        "The policy wording does exclude {excl}. The insurer applied a term that is part of the contract.",
        "{excl} is listed as a permanent exclusion in the policy. On these documents the rejection is likely to stand.",
        "The cited exclusion ({excl}) appears in the policy excerpt, so there is no clear ground to contest.",
    ],
    "inpatient_long_stay": [
        "The patient was in hospital for {h} hours. A stay of 24 hours or more counts as inpatient hospitalisation, so the rejection looks wrong.",
        "The stay lasted {h} hours, which meets the 24-hour requirement for hospitalisation under the policy.",
        "Admission to discharge was {h} hours. That is an inpatient stay, not an outpatient visit.",
        "With a {h}-hour stay the 24-hour condition is satisfied, so saying hospitalisation was not needed is open to challenge.",
    ],
    "inpatient_daycare": [
        "The stay was {h} hours, but the treatment is on the policy's list of day care procedures, which are covered without a 24-hour stay.",
        "This procedure is a listed day care procedure in the policy, so the short {h}-hour stay is not a ground to reject.",
        "Day care procedures are covered even when the stay is under 24 hours, and this treatment appears in the policy's day care list.",
        "The policy lists this treatment as a covered day care procedure. The {h}-hour stay does not defeat the claim.",
    ],
    "short_stay_not_daycare": [
        "The stay was {h} hours, under 24, and the treatment is not on the policy's day care list. It is not clearly wrong, but ask for the medical opinion relied on.",
        "With a {h}-hour stay and no matching day care procedure in the policy, the rejection may hold. The treating doctor's justification could still change it.",
        "The stay was shorter than 24 hours ({h} hours) and the treatment is not a listed day care procedure. Ask the insurer for its medical reasoning.",
        "Neither the 24-hour condition nor the day care list helps here ({h} hours). A letter from the treating doctor on why admission was needed is worth getting.",
    ],
    "room_rent_within_limit": [
        "The room was charged at Rs {chg} per day and the policy limit is Rs {lim} per day. The room was within entitlement, so no proportionate deduction should apply.",
        "Room rent charged (Rs {chg}) does not exceed the policy limit (Rs {lim}). The deduction looks wrong.",
        "The policy allows Rs {lim} per day and the hospital charged Rs {chg}. There is no excess to justify a proportionate deduction.",
        "A proportionate deduction needs a room above the limit. Here the charge of Rs {chg} is within the Rs {lim} limit.",
    ],
    "room_rent_over_limit": [
        "The room cost Rs {chg} per day against a limit of Rs {lim}, so some deduction is allowed. Ask for the calculation and check it line by line.",
        "Room rent charged (Rs {chg}) is above the policy limit (Rs {lim}). A deduction is permitted, but the amount should be verified.",
        "Because the room was above entitlement (Rs {chg} against Rs {lim}), the insurer can deduct proportionately. Whether the maths is right is worth checking.",
        "The limit is Rs {lim} per day and the room was Rs {chg}. The deduction is not wrong in principle; ask for the working.",
    ],
    "documents_or_delay": [
        "This is a procedural rejection. Send the pending documents or a written explanation for the delay and ask for the claim to be reopened.",
        "The claim was closed on documents or timing, not on merits. Resubmitting with an explanation is worth doing.",
        "Rejections for missing papers or late intimation can often be reopened. Provide what is pending and explain any delay in writing.",
        "Nothing here says the treatment is not covered. Supply the documents or the reason for delay and request reconsideration.",
    ],
    "premium_within_grace": [
        "The renewal premium was received within the grace period after the due date, so the policy was in force and the rejection looks wrong.",
        "Payment was made inside the grace period stated in the policy. Cover continues in that case, so the policy had not lapsed.",
        "The dates show the premium was paid before the grace period ended. The insurer cannot treat the policy as lapsed.",
        "The policy gives a grace period for renewal and the premium arrived within it. The lapse ground does not hold.",
    ],
    "policy_lapsed": [
        "The renewal premium was not received within the grace period, so the policy was not in force at admission. The rejection looks valid.",
        "Payment came after the grace period ended, or not at all. On these dates the policy had lapsed.",
        "The documents show the premium was not paid in time. A claim arising while the policy was lapsed is not payable.",
        "The grace period ended before any premium was received. There is no clear ground to contest the lapse.",
    ],
    "restore_benefit_unused": [
        "The sum insured is used up, but the policy has a restore benefit that has not been used this policy year. Ask why it was not applied.",
        "The policy schedule shows a restore benefit not yet utilised this year. It may reinstate the sum insured for this claim, subject to its conditions.",
        "An unused restore benefit is available on the policy. Whether it applies to this claim depends on its conditions, so ask the insurer.",
        "The insurer says the cover is exhausted but does not address the unused restore benefit on the schedule. That needs an answer.",
    ],
    "sum_insured_exhausted": [
        "The sum insured for the year has been used and the policy has no unused restore benefit. The rejection looks valid.",
        "Earlier claims exhausted the cover and there is no restore benefit left to draw on this policy year.",
        "With the sum insured exhausted and no restore benefit available, nothing more is payable this policy year.",
        "The documents show no remaining cover: the sum insured is used up and the restore benefit is absent or already used.",
    ],
    "uncategorised": [
        "This ground does not fit a standard pattern. Ask the insurer for the exact clause and the evidence it relied on before deciding.",
        "The letter gives too little to judge. Request the policy clause and supporting records in writing.",
        "It is not clear from the documents whether this rejection is right. Ask for the clause and the basis of the decision.",
        "The reason given cannot be checked against the policy excerpt. A written request for the clause relied on is the next step.",
    ],
}

MISSING: dict[str, list[str]] = {
    "ped_disclosed_in_proposal": ["whether {cond} was declared in the proposal form", "what was declared in the proposal form"],
    "accident_exempt_in_wording": ["whether the policy wording exempts accidents from the {wp}-month waiting period", "what the wording says about accidents and waiting periods"],
    "exclusion_in_policy_wording": ["whether the exclusion for {excl} is actually in the policy wording", "the policy's list of exclusions"],
    "is_listed_daycare_procedure": ["whether the treatment is on the policy's day care list", "the policy's list of day care procedures"],
    "room_rent_limit_per_day": ["the room rent limit under the policy", "what room rent the policy allows"],
    "premium_paid_within_grace": ["when the renewal premium was received and the grace period allowed", "the payment date and grace period"],
    "restore_benefit_available_unused": ["whether the policy has an unused restore benefit", "whether a restore benefit applies"],
}
MISSING_FRAMES = [
    "The documents do not show {what}. Without that the rejection cannot be judged either way, so ask the insurer.",
    "It is not possible to tell {what} from these papers. Get that in writing before deciding whether to contest.",
    "A key fact is missing: {what}. The rejection may or may not be right.",
    "Neither the letter nor the policy excerpt shows {what}. Ask for it.",
]


def reason_for(result: RuleResult, facts: CaseFacts, rng: random.Random) -> str:
    fields = dict(
        m=facts.months_continuous_coverage,
        wp=facts.waiting_period_months,
        h=facts.hospital_stay_hours,
        lim=facts.room_rent_limit_per_day,
        chg=facts.room_rent_charged_per_day,
        cond=facts.condition_named_by_insurer or "the condition",
        excl=facts.exclusion_cited or "the treatment",
    )
    if result.missing_facts:
        what = " and ".join(rng.choice(MISSING[f]) for f in result.missing_facts)
        text = rng.choice(MISSING_FRAMES).format(what=what)
    else:
        code = result.reason_codes[0]
        if code == "inpatient_stay_or_daycare":
            code = "inpatient_long_stay" if (facts.hospital_stay_hours or 0) >= 24 else "inpatient_daycare"
        text = rng.choice(TEMPLATES[code])
    text = text.format(**fields)
    return text[0].upper() + text[1:]
