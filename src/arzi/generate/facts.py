"""Sample structured cases: gold CaseFacts plus a brief for the teacher model.

Each case is steered towards one scenario (a specific rule outcome), but the
label itself always comes from rules.evaluate, never from the sampler. All
names, insurers and numbers are fictional.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from arzi.rules import evaluate, months_between
from arzi.schema import CaseFacts, Category, Verdict

C, W, V = Verdict.LIKELY_CONTESTABLE, Verdict.WORTH_ASKING, Verdict.LIKELY_VALID

# approximate category mix (SPEC section 6)
CATEGORY_MIX: dict[Category, float] = {
    Category.NON_DISCLOSURE_PED: 0.25,
    Category.WAITING_PERIOD: 0.20,
    Category.PERMANENT_EXCLUSION: 0.10,
    Category.NO_HOSPITALISATION_NEEDED: 0.08,
    Category.ROOM_RENT_PROPORTIONATE: 0.10,
    Category.DOCUMENTS_OR_LATE_INTIMATION: 0.10,
    Category.POLICY_LAPSED: 0.06,
    Category.SUM_INSURED_EXHAUSTED: 0.06,
    Category.OTHER: 0.05,
}

# (scenario, weight, verdict the rules must give). Weights put LIKELY_VALID at
# about a third of the whole set.
SCENARIOS: dict[Category, list[tuple[str, float, Verdict]]] = {
    Category.NON_DISCLOSURE_PED: [
        ("moratorium", 0.17, C),
        ("disclosed", 0.17, C),
        ("unrelated", 0.10, W),
        ("disclosure_unknown", 0.08, W),
        ("valid", 0.48, V),
    ],
    Category.WAITING_PERIOD: [
        ("served", 0.18, C),
        ("accident_initial", 0.10, C),
        ("accident_exempt", 0.10, C),
        ("accident_wording_unknown", 0.10, W),
        ("not_served", 0.38, V),
        ("accident_not_exempt", 0.14, V),
    ],
    Category.PERMANENT_EXCLUSION: [("not_in_wording", 0.35, C), ("wording_unknown", 0.15, W), ("in_wording", 0.50, V)],
    Category.NO_HOSPITALISATION_NEEDED: [
        ("long_stay", 0.30, C),
        ("daycare", 0.25, C),
        ("short_stay", 0.30, W),
        ("daycare_list_unknown", 0.15, W),
    ],
    Category.ROOM_RENT_PROPORTIONATE: [("within_limit", 0.40, C), ("over_limit", 0.50, W), ("limit_unknown", 0.10, W)],
    Category.DOCUMENTS_OR_LATE_INTIMATION: [("missing_documents", 0.5, W), ("late_intimation", 0.3, W), ("late_submission", 0.2, W)],
    Category.POLICY_LAPSED: [("within_grace", 0.40, C), ("payment_unknown", 0.10, W), ("lapsed", 0.50, V)],
    Category.SUM_INSURED_EXHAUSTED: [("restore_unused", 0.35, W), ("restore_unknown", 0.15, W), ("exhausted", 0.50, V)],
    Category.OTHER: [("non_network", 0.25, W), ("investigation", 0.25, W), ("treatment_protocol", 0.25, W), ("copay_dispute", 0.25, W)],
}

MORATORIUM_EDGE = range(55, 66)  # 55 to 65 months inclusive

INSURERS = [
    "Suraksha General Insurance",
    "Aarogya Kavach Health Insurance",
    "Nirbhay Health Assurance",
    "Sanjeevani Bima Company",
    "Dhanraksha General Insurance",
    "Samriddhi Health Insurance",
    "Jeevan Setu General Insurance",
]
TPAS = ["MediSetu TPA Services", "CareBridge Health TPA", "Swasthya Mitra TPA", "Arogya Link TPA"]
HOSPITALS = [
    "Shanti Multispeciality Hospital, Pune",
    "Navjeevan Hospital, Ahmedabad",
    "Sai Krupa Nursing Home, Nashik",
    "Lotus Care Hospital, Hyderabad",
    "Shree Ganesh Hospital, Indore",
    "Sunrise Medical Centre, Lucknow",
    "Kaveri Speciality Hospital, Coimbatore",
    "Aastha Hospital, Jaipur",
]
FIRST_NAMES = ["Ramesh", "Sunita", "Imran", "Kavita", "Joseph", "Meenakshi", "Harpreet", "Anil", "Farida", "Devendra", "Lakshmi", "Prakash", "Shabnam", "Vinod", "Geeta"]
LAST_NAMES = ["Kulkarni", "Sharma", "Shaikh", "Patel", "D'Souza", "Iyer", "Gill", "Yadav", "Banerjee", "Reddy", "Joshi", "Nair", "Chauhan", "Mehta", "Das"]

# (condition, keyword that proves it is in a text, related claim, unrelated claim)
PED_PAIRS = [
    ("Type 2 diabetes mellitus", "diabetes", "diabetic ketoacidosis", "acute appendicitis (appendicectomy)"),
    ("hypertension", "hypertension", "hypertensive heart disease with heart failure", "dengue fever"),
    ("bronchial asthma", "asthma", "acute severe asthma exacerbation", "inguinal hernia repair"),
    ("chronic kidney disease", "kidney disease", "end-stage renal disease requiring dialysis", "typhoid fever"),
    ("coronary artery disease", "coronary", "acute myocardial infarction with angioplasty", "cataract surgery"),
    ("epilepsy", "epilepsy", "status epilepticus", "acute gastroenteritis"),
    ("chronic hepatitis B", "hepatitis", "decompensated liver cirrhosis", "ureteroscopic removal of a kidney stone"),
]
SPECIFIC_DISEASES = ["cataract", "inguinal hernia", "kidney stones", "gall bladder stones", "knee osteoarthritis (joint replacement)", "piles (haemorrhoids)", "chronic sinusitis", "benign prostatic hyperplasia"]
ACCIDENT_SPECIFIC = [
    ("traumatic cataract after a road traffic accident", "cataract"),
    ("knee joint replacement after a fracture sustained in a fall from stairs", "joint replacement"),
    ("spinal disc surgery after a road traffic accident", "intervertebral disc prolapse"),
]
ACUTE_ILLNESSES = ["dengue fever", "typhoid fever", "community-acquired pneumonia", "acute gastroenteritis", "malaria"]
ACCIDENT_INJURIES = ["fracture of the femur after a road traffic accident", "head injury after a two-wheeler accident", "forearm fracture after a fall from a ladder"]
# (exclusion as cited, keyword, treatment claimed)
EXCLUSIONS = [
    ("cosmetic or plastic surgery", "cosmetic", "rhinoplasty"),
    ("infertility and assisted reproduction treatment", "infertility", "an IVF cycle"),
    ("obesity and weight control treatment", "obesity", "bariatric surgery"),
    ("dental treatment not arising from an accident", "dental", "root canal treatment with crowns"),
    ("correction of refractive error below 7.5 dioptres", "refractive", "LASIK surgery"),
    ("unproven or experimental treatment", "experimental", "stem cell therapy for the knee"),
    ("treatment for alcohol or substance abuse", "alcohol", "de-addiction treatment"),
    ("sleep apnoea devices and external aids", "apnoea", "a CPAP device"),
]
# (procedure, keyword)
DAYCARE = [
    ("cataract surgery (phacoemulsification)", "cataract"),
    ("a chemotherapy session", "chemotherapy"),
    ("haemodialysis", "dialysis"),
    ("tonsillectomy", "tonsillectomy"),
    ("lithotripsy for a kidney stone", "lithotripsy"),
    ("coronary angiography", "angiography"),
    ("arthroscopic knee surgery", "arthroscop"),
]
SHORT_STAYS = [
    "observation and IV fluids for acute gastritis",
    "IV antibiotics for a urinary tract infection",
    "evaluation of chest pain (ECG and troponin)",
    "management of a severe migraine attack",
    "viral fever with dehydration",
    "nebulisation for wheezing",
]
DOCUMENTS = ["original discharge summary", "itemised final bill with break-up", "all investigation reports", "KYC documents of the proposer", "cancelled cheque for NEFT", "indoor case papers", "attending doctor's certificate on duration of illness"]

DATE_FORMATS = ["{d} {B} {Y}", "{dd}/{mm}/{Y}", "{dd}-{b}-{Y}", "{dd}.{mm}.{Y}", "{B} {d}, {Y}"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
EARLIEST = date(2019, 1, 1)
LATEST_ADMISSION = date(2026, 9, 28)


def format_date(d: date, fmt: str) -> str:
    B = MONTHS[d.month - 1]
    return fmt.format(d=d.day, dd=f"{d.day:02d}", mm=f"{d.month:02d}", B=B, b=B[:3], Y=d.year)


def format_inr(n: int) -> str:
    """Indian digit grouping: 150000 -> 1,50,000."""
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return ",".join([head, *groups, tail])


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.year * 12 + d.month - 1 + n, 12)
    return date(y, m + 1, min(d.day, 28))


def allocate(n: int, weights: list[float], rng: random.Random) -> list[int]:
    """Split n into integer counts proportional to weights (largest remainder)."""
    total = sum(weights)
    exact = [n * w / total for w in weights]
    counts = [int(x) for x in exact]
    order = sorted(range(len(weights)), key=lambda i: (exact[i] - counts[i], rng.random()), reverse=True)
    for i in order[: n - sum(counts)]:
        counts[i] += 1
    return counts


@dataclass
class Case:
    case_id: str
    category: Category
    scenario: str
    facts: CaseFacts  # gold: exactly what the two documents state
    letter_points: list[str]  # what the rejection letter must say
    policy_points: list[str]  # what the policy excerpt must say
    letter_must: list[str] = field(default_factory=list)  # literal strings checked after generation
    policy_must: list[str] = field(default_factory=list)
    policy_must_not: list[str] = field(default_factory=list)

    @property
    def is_moratorium_edge(self) -> bool:
        return self.category is Category.NON_DISCLOSURE_PED and self.facts.months_continuous_coverage in MORATORIUM_EDGE


class _Builder:
    def __init__(self, rng: random.Random):
        self.rng = rng
        self.fmt = rng.choice(DATE_FORMATS)
        self.rs = rng.choice(["Rs. ", "Rs ", "INR ", "₹"])
        self.facts: dict = {"is_accident": False}
        self.letter: list[str] = []
        self.policy: list[str] = []
        self.letter_must: list[str] = []
        self.policy_must: list[str] = []
        self.policy_must_not: list[str] = []
        self.diagnosis = ""
        self.inception: date | None = None
        self.admission: date | None = None
        self.show_policy_period = True
        self.state_room_rent: bool | None = None  # None = decide at random
        self.sum_insured = rng.choice([300000, 500000, 500000, 1000000, 1500000])
        self.force_edge = False  # non-disclosure only: put cover in the 55 to 65 month band

    def d(self, value: date) -> str:
        return format_date(value, self.fmt)

    def money(self, n: int) -> str:
        return f"{self.rs}{format_inr(n)}"

    def set_dates(self, months: int, min_extra_days: int = 0) -> None:
        """Pick admission and inception dates giving exactly `months` whole months of cover."""
        lo = add_months(date(2019, 2, 1), months)
        span = (LATEST_ADMISSION - lo).days
        admission = lo + timedelta(days=self.rng.randint(0, span))
        admission = admission.replace(day=min(admission.day, 28))
        inception = add_months(admission, -months) - timedelta(days=self.rng.randint(min_extra_days, 25))
        assert inception >= EARLIEST and months_between(inception, admission) == months
        self.inception, self.admission = inception, admission


def _ped(b: _Builder, s: str) -> None:
    rng = b.rng
    cond, key, related_dx, unrelated_dx = rng.choice(PED_PAIRS)
    if s == "moratorium":
        months = rng.choice([60, 60, 61, 62, 63, 64, 65]) if b.force_edge or rng.random() < 0.5 else rng.randint(66, 88)
    elif b.force_edge or rng.random() < (0.25 if s == "valid" else 0.15):
        months = rng.randint(55, 59)
    else:
        months = rng.randint(2, 54)
    b.set_dates(months)
    disclosed = {"moratorium": rng.choice([False, False, None]), "disclosed": True, "unrelated": False, "disclosure_unknown": None, "valid": False}[s]
    related = {"unrelated": False, "valid": True}.get(s, rng.random() < 0.7)
    b.diagnosis = related_dx if related else unrelated_dx
    b.facts.update(condition_named_by_insurer=cond, ped_disclosed_in_proposal=disclosed, condition_related_to_claim=related)
    b.letter += [
        f"Ground of rejection: non-disclosure of a pre-existing disease. The insurer says the insured had {cond} before the policy started and did not declare it in the proposal form.",
        f"The insurer relies on hospital records noting a history of {cond} for {rng.randint(7, 15)} years.",
    ]
    if disclosed is True:
        b.policy.append(f"The schedule has a line 'Pre-existing diseases declared in proposal form' and it lists: {cond}.")
        b.policy_must.append(key)
    elif disclosed is False:
        b.policy.append("The schedule has a line 'Pre-existing diseases declared in proposal form' and it says: None declared.")
        b.policy_must_not.append(key)
    else:
        b.policy.append("Do NOT include any line about pre-existing diseases declared in the proposal form, and do not name any disease of the insured.")
        b.policy_must_not.append(key)


def _waiting(b: _Builder, s: str) -> None:
    rng = b.rng
    ped_wait = rng.choice([36, 48])
    accident = s.startswith("accident")
    if s == "accident_initial":
        kind = "initial"
    elif accident:
        kind = "specific"
    else:
        kind = rng.choices(["specific", "ped", "initial"], [0.5, 0.35, 0.15])[0]
    wp = {"initial": 1, "specific": 24, "ped": ped_wait}[kind]
    if s == "served":
        months = wp + rng.choice([0, 0, 1, 2, rng.randint(3, 30)])
    elif wp == 1:
        months = 0
    else:
        months = wp - rng.choice([1, 1, 2, 3, rng.randint(4, wp - 1)])
    b.set_dates(months, min_extra_days=3 if months == 0 else 0)

    if accident:
        exempt = {"accident_initial": rng.choice([None, None, None, False, True]), "accident_exempt": True, "accident_wording_unknown": None, "accident_not_exempt": False}[s]
    else:
        exempt = rng.choice([True, False]) if rng.random() < 0.25 else None

    declared = None
    if kind == "initial":
        b.diagnosis = named = rng.choice(ACCIDENT_INJURIES if accident else ACUTE_ILLNESSES)
        label, period = "initial waiting period", "30 days"
    elif kind == "specific":
        if accident:
            b.diagnosis, named = rng.choice(ACCIDENT_SPECIFIC)
        else:
            b.diagnosis = named = rng.choice(SPECIFIC_DISEASES)
        label, period = "specific disease waiting period", rng.choice(["24 months", "2 years", "two years"])
    else:
        named, key, b.diagnosis, _ = rng.choice(PED_PAIRS)
        declared = (named, key)
        label = "pre-existing disease waiting period"
        period = rng.choice([f"{ped_wait} months", f"{ped_wait // 12} years"])
    b.facts.update(is_accident=accident, accident_exempt_in_wording=exempt, waiting_period_months=wp, condition_named_by_insurer=named)
    b.letter.append(f"Ground of rejection: the claim falls within the {label} of {period}" + (f" applicable to {named}." if kind != "initial" else " from the start of the policy."))
    if accident:
        b.letter.append("The letter itself records that the injury or treatment followed an accident, but still applies the waiting period.")
    if declared:
        b.facts["ped_disclosed_in_proposal"] = True
        b.policy.append(f"The schedule has a line 'Pre-existing diseases declared in proposal form' and it lists: {declared[0]}.")
        b.policy_must.append(declared[1])
    if exempt is True:
        b.policy.append("The waiting period clause must say clearly that the waiting periods do not apply to claims arising out of an accident.")
    elif exempt is False:
        b.policy.append("The waiting period clause must say clearly that only the initial 30-day waiting period is waived for accidents, and that the specific disease and pre-existing disease waiting periods apply even when treatment follows an accident.")
    else:
        b.policy.append("Do NOT say anything about whether accidents are exempt from any waiting period. Do not use the word accident anywhere in the policy excerpt.")
        b.policy_must_not.append("accident")
    b.ped_wait = ped_wait


def _exclusion(b: _Builder, s: str) -> None:
    rng = b.rng
    b.set_dates(rng.randint(2, 80))
    cited, key, treatment = rng.choice(EXCLUSIONS)
    b.diagnosis = treatment
    in_wording = {"not_in_wording": False, "wording_unknown": None, "in_wording": True}[s]
    b.facts.update(exclusion_cited=cited, exclusion_in_policy_wording=in_wording)
    b.letter.append(f"Ground of rejection: the treatment is permanently excluded under the policy, citing the exclusion for {cited}.")
    others = [e[0] for e in rng.sample([e for e in EXCLUSIONS if e[1] != key], 4)]
    if in_wording is None:
        b.policy.append("Do NOT list any exclusions. Say only that exclusions are 'as per the policy wording document', which is not reproduced.")
        b.policy_must_not.append(key)
    else:
        listed = others + ([cited] if in_wording else [])
        rng.shuffle(listed)
        b.policy.append("The excerpt has a section 'Permanent exclusions' listing exactly these and no others: " + "; ".join(listed) + ".")
        (b.policy_must if in_wording else b.policy_must_not).append(key)


def _no_hospitalisation(b: _Builder, s: str) -> None:
    rng = b.rng
    b.set_dates(rng.randint(2, 80))
    listed = None
    if s == "long_stay":
        hours = rng.choice([24, 24, 26, 30, 36, 48, 72, 96])
        b.diagnosis, key = rng.choice(SHORT_STAYS), None
        listed = rng.choice([False, False, None])
    elif s == "daycare":
        hours = rng.randint(3, 10)
        b.diagnosis, key = rng.choice(DAYCARE)
        listed = True
    else:
        hours = rng.choice([4, 6, 8, 10, 12, 16, 20, 22, 23])
        b.diagnosis, key = rng.choice(SHORT_STAYS), None
        listed = False if s == "short_stay" else None
    b.facts.update(hospital_stay_hours=hours, is_listed_daycare_procedure=listed)
    b.letter.append("Ground of rejection: hospitalisation was not medically necessary; the treatment could have been given on an outpatient (OPD) basis.")
    start_hour = rng.randint(6, 22)
    end = start_hour + hours
    discharge = b.admission + timedelta(days=end // 24)
    if rng.random() < 0.5:
        b.letter.append(f"State the length of stay directly: the patient was in hospital for {hours} hours.")
        b.letter_must.append(f"{hours} hours")
    else:
        b.letter.append(
            f"Do not state the number of hours. Instead give the times: admitted at {start_hour:02d}:00 hrs on the admission date and discharged at {end % 24:02d}:00 hrs on {b.d(discharge)}."
        )
        b.letter_must += [f"{start_hour:02d}:00", f"{end % 24:02d}:00", b.d(discharge)]
    if listed is None:
        b.policy.append("Do NOT include any list of day care procedures. Say only that day care procedures are covered 'as per Annexure', which is not reproduced.")
        b.policy_must_not.append("chemotherapy")
    else:
        pool = [p for p in DAYCARE if p[1] != key]
        chosen = rng.sample(pool, 4) + ([(b.diagnosis, key)] if listed and key else [])
        rng.shuffle(chosen)
        b.policy.append("The excerpt has a section 'Day care procedures covered (stay under 24 hours)' listing exactly these and no others: " + "; ".join(p[0] for p in chosen) + ".")
        if key:
            b.policy_must.append(key)


def _room_rent(b: _Builder, s: str) -> None:
    rng = b.rng
    b.set_dates(rng.randint(2, 80))
    b.diagnosis = rng.choice(ACUTE_ILLNESSES + ["laparoscopic cholecystectomy", "total knee replacement"])
    limit = rng.choice([2000, 3000, 4000, 5000, 6000, 7500, 10000])
    charged = limit - rng.choice([0, 0, 500, 1000, 1500]) if s == "within_limit" else limit + rng.choice([500, 1000, 1500, 2500, 4000, 5000])
    days = rng.randint(3, 8)
    bill = charged * days + rng.randint(40, 300) * 1000
    deducted = rng.randint(8, 60) * 1000
    b.facts.update(room_rent_charged_per_day=charged, room_rent_limit_per_day=None if s == "limit_unknown" else limit)
    b.state_room_rent = s != "limit_unknown"
    b.room_limit = limit
    b.letter += [
        f"This is a short-settlement letter, not a full rejection: out of a bill of {b.money(bill)}, {b.money(deducted)} was deducted as a proportionate deduction because the room category was above entitlement.",
        f"The room actually occupied was charged at {b.money(charged)} per day for {days} days. Do NOT state the room rent limit or entitlement amount in the letter.",
    ]
    b.letter_must += [str(charged), str(bill), str(deducted)]
    b.claim_amount = bill


def _documents(b: _Builder, s: str) -> None:
    rng = b.rng
    b.set_dates(rng.randint(2, 80))
    b.diagnosis = rng.choice(ACUTE_ILLNESSES + SPECIFIC_DISEASES)
    if s == "missing_documents":
        docs = rng.sample(DOCUMENTS, rng.randint(2, 4))
        b.letter.append("Ground of rejection: the claim is closed for non-submission of required documents despite reminders. Documents not received: " + "; ".join(docs) + ".")
    elif s == "late_intimation":
        delay = rng.randint(4, 20)
        b.letter.append(f"Ground of rejection: late intimation. The hospitalisation was intimated {delay} days after admission, against the policy condition requiring intimation within {rng.choice([24, 48])} hours of emergency admission.")
    else:
        delay = rng.randint(40, 120)
        b.letter.append(f"Ground of rejection: late submission. The reimbursement claim documents were submitted {delay} days after discharge, against the policy condition of 30 days.")


def _lapsed(b: _Builder, s: str) -> None:
    rng = b.rng
    years = rng.randint(1, 5)
    lo = date(2019 + years, 2, 1)
    due = lo + timedelta(days=rng.randint(0, (date(2026, 7, 1) - lo).days))
    due = due.replace(day=min(due.day, 28))
    grace = rng.choice([15, 30])
    b.inception = add_months(due, -12 * years)
    b.admission = due + timedelta(days=rng.randint(2, grace + 45))
    b.diagnosis = rng.choice(ACUTE_ILLNESSES + ["acute appendicitis (appendicectomy)"])
    b.show_policy_period = False
    b.policy.append(f"Previous policy period: {b.d(add_months(due, -12))} to {b.d(due - timedelta(days=1))}. Renewal premium due date: {b.d(due)}.")
    b.policy_must.append(b.d(due))
    b.letter.append(f"Ground of rejection: the policy had lapsed and was not in force on the date of admission. Renewal was due on {b.d(due)}.")
    if s == "payment_unknown":
        b.facts["premium_paid_within_grace"] = None
        b.letter.append("Say only that the renewal premium 'was not received in time'. Do NOT give any date on which the premium was paid or received.")
        b.policy.append("Do NOT state any grace period.")
        return
    within = s == "within_grace"
    b.facts["premium_paid_within_grace"] = within
    b.policy.append(f"Grace period for renewal: {grace} days from the due date.")
    b.policy_must.append(f"{grace} days")
    if within:
        paid = due + timedelta(days=rng.randint(1, grace))
    elif rng.random() < 0.5:
        paid = due + timedelta(days=grace + rng.randint(1, 40))
    else:
        b.letter.append("State that no renewal premium has been received at all up to the date of this letter.")
        return
    b.letter.append(f"State that the renewal premium was received on {b.d(paid)}.")
    b.letter_must.append(b.d(paid))


def _sum_insured(b: _Builder, s: str) -> None:
    rng = b.rng
    b.set_dates(rng.randint(8, 80))
    b.diagnosis = rng.choice(ACUTE_ILLNESSES + ["acute myocardial infarction with angioplasty", "total knee replacement"])
    b.letter.append(f"Ground of rejection: the sum insured of {b.money(b.sum_insured)} for the current policy year has already been exhausted by earlier claims paid this year, so nothing is payable.")
    if s == "restore_unused":
        available = True
        b.policy.append("The schedule has a line: 'Restore benefit: 100% of sum insured, once per policy year. Restore benefit utilised in current policy year: No'.")
        b.policy_must.append("restore")
    elif s == "restore_unknown":
        available = None
        b.policy.append("Do NOT mention any restore, recharge, reinstatement or refill benefit anywhere.")
        b.policy_must_not += ["restore", "recharge"]
    else:
        available = False
        if rng.random() < 0.5:
            b.policy.append("The schedule has a line: 'Restore benefit: Not opted'.")
        else:
            b.policy.append("The schedule has a line: 'Restore benefit: 100% of sum insured, once per policy year. Restore benefit utilised in current policy year: Yes'.")
        b.policy_must.append("restore")
    b.facts["restore_benefit_available_unused"] = available
    b.letter.append("Do NOT mention any restore, recharge or reinstatement benefit in the letter.")


def _other(b: _Builder, s: str) -> None:
    rng = b.rng
    b.set_dates(rng.randint(2, 80))
    b.diagnosis = rng.choice(ACUTE_ILLNESSES + SPECIFIC_DISEASES)
    b.letter.append(
        {
            "non_network": "Ground of rejection: treatment was taken at a hospital on the insurer's list of excluded (de-listed) providers, where only emergency stabilisation is payable.",
            "investigation": "Ground of rejection: field investigation found discrepancies between the hospital's indoor case papers and the billing records, so the claim is not admissible. Give no further detail.",
            "treatment_protocol": "Ground of rejection: the line of treatment and length of stay were not in line with standard treatment protocols for the diagnosis, so the claim is not payable.",
            "copay_dispute": "Ground of rejection: the insured refused to bear the applicable co-payment and zone-based deduction, so the claim file has been closed.",
        }[s]
    )


_SAMPLERS = {
    Category.NON_DISCLOSURE_PED: _ped,
    Category.WAITING_PERIOD: _waiting,
    Category.PERMANENT_EXCLUSION: _exclusion,
    Category.NO_HOSPITALISATION_NEEDED: _no_hospitalisation,
    Category.ROOM_RENT_PROPORTIONATE: _room_rent,
    Category.DOCUMENTS_OR_LATE_INTIMATION: _documents,
    Category.POLICY_LAPSED: _lapsed,
    Category.SUM_INSURED_EXHAUSTED: _sum_insured,
    Category.OTHER: _other,
}


def sample_case(rng: random.Random, case_id: str, category: Category, scenario: str, force_edge: bool = False) -> Case:
    b = _Builder(rng)
    b.force_edge = force_edge
    _SAMPLERS[category](b, scenario)
    inception, admission = b.inception, b.admission
    months = months_between(inception, admission)

    insurer = rng.choice(INSURERS)
    insured = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
    policy_no = f"{''.join(w[0] for w in insurer.split()[:2])}/{rng.choice(['HLT', 'IND', 'FLT'])}/{inception.year}/{rng.randint(100000, 999999)}"
    claim_no = f"CLM-{admission.year}-{rng.randint(1000000, 9999999)}"
    crc = rng.random() < 0.35
    claim_amount = getattr(b, "claim_amount", rng.randint(25, 600) * 1000)
    letter_date = min(admission + timedelta(days=rng.randint(12, 70)), date(2026, 10, 10))

    letter = [
        f"Issued by {insurer}" + (f" through its TPA, {rng.choice(TPAS)}" if rng.random() < 0.4 else "") + f". Letter date: {b.d(letter_date)}.",
        f"Addressed to the insured, {insured}. Policy number {policy_no}. Claim number {claim_no}.",
        f"Hospital: {rng.choice(HOSPITALS)}. Date of admission: {b.d(admission)}. Diagnosis or treatment: {b.diagnosis}.",
        f"Amount claimed: {b.money(claim_amount)}.",
        *b.letter,
        "State that this decision was reviewed and approved by the insurer's Claims Review Committee."
        if crc
        else "Do NOT mention any Claims Review Committee or any committee review.",
    ]
    letter_must = [b.d(admission), policy_no, *b.letter_must]

    ported = months >= 14 and rng.random() < 0.25
    if ported:
        port_date = add_months(inception, 12 * rng.randint(1, months // 12))
        cover = f"The policy was ported from a previous insurer. Show 'Date of first inception / continuous cover since: {b.d(inception)}' and separately 'Policy with {insurer} since: {b.d(port_date)}'."
        if b.rng.random() < 0.5:
            letter.append(f"When the letter mentions how old the policy is, it counts only from {b.d(port_date)} (the date the policy came to this insurer) and does not mention the earlier ported cover.")
    else:
        cover = f"Show 'Date of first inception (continuous cover since)': {b.d(inception)}."
    policy = [
        f"Policy schedule of {insurer}. Policy number {policy_no}. Insured: {insured}.",
        cover,
        f"Sum insured: {b.money(b.sum_insured)}.",
    ]
    if b.show_policy_period:
        start = add_months(inception, 12 * (months // 12))
        policy.append(f"Current policy period: {b.d(start)} to {b.d(add_months(start, 12) - timedelta(days=1))}.")
    state_rent = b.state_room_rent if b.state_room_rent is not None else rng.random() < 0.6
    if state_rent:
        limit = getattr(b, "room_limit", rng.choice([3000, 4000, 5000, 7500, 10000]))
        b.facts["room_rent_limit_per_day"] = limit
        policy.append(f"Room rent limit: {b.money(limit)} per day.")
        b.policy_must.append(str(limit))
    else:
        policy.append("Do NOT state any room rent limit or room category entitlement.")
    ped_wait = getattr(b, "ped_wait", rng.choice([36, 48]))
    policy.append(f"Waiting periods section: initial waiting period 30 days; specific diseases and procedures 24 months; pre-existing diseases {ped_wait} months.")
    policy += b.policy

    facts = CaseFacts(
        policy_inception_date=inception,
        admission_date=admission,
        months_continuous_coverage=months,
        crc_approval_mentioned=crc,
        **b.facts,
    )
    case = Case(
        case_id=case_id,
        category=category,
        scenario=scenario,
        facts=facts,
        letter_points=letter,
        policy_points=policy,
        letter_must=letter_must,
        policy_must=[b.d(inception), *b.policy_must],
        policy_must_not=b.policy_must_not,
    )
    expected = next(v for name, _, v in SCENARIOS[category] if name == scenario)
    got = evaluate(category, facts).verdict
    assert got is expected, f"{case_id} {category.value}/{scenario}: rules gave {got}, sampler meant {expected}"
    return case


def sample_cases(n: int, seed: int, prefix: str, min_moratorium_edge: int = 0) -> list[Case]:
    """n cases with the SPEC category mix and per-category scenario weights, deterministic in seed.

    `min_moratorium_edge` forces that many non-disclosure cases into the 55 to 65
    month band (used for the eval set, so the edge metric rests on enough cases).
    """
    rng = random.Random(f"{seed}:{prefix}:plan")
    plan: list[tuple[Category, str]] = []
    categories = list(CATEGORY_MIX)
    for category, count in zip(categories, allocate(n, list(CATEGORY_MIX.values()), rng)):
        scenarios = SCENARIOS[category]
        for (name, _, _), k in zip(scenarios, allocate(count, [w for _, w, _ in scenarios], rng)):
            plan += [(category, name)] * k
    rng.shuffle(plan)
    ped = [i for i, (category, _) in enumerate(plan) if category is Category.NON_DISCLOSURE_PED]
    forced = set(random.Random(f"{seed}:{prefix}:edge").sample(ped, min(min_moratorium_edge, len(ped))))
    return [
        sample_case(random.Random(f"{seed}:{prefix}:{i}"), f"{prefix}-{i:04d}", category, scenario, i in forced)
        for i, (category, scenario) in enumerate(plan)
    ]
