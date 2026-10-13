# Spot-check: 10 random generated cases

7 from train, 3 from eval_synth (held-out styles). Check that the letter and policy really state the facts in the label, and that the verdict follows from RULES.md.

## 1. `train-0333`: waiting_period / not_served -> **likely_valid**

Style: polite customer-care style letter that apologises a lot and buries the actual ground in the middle. Noisy: True.

```text
REJECTION LETTER:
Nirbhay Health Assurance  
c/o CareBridge Health TPA  
3rd Floor, Health Plaza New Delhi
– 110001  
Phone: 1800‑123‑4567  
Email: support@nirbhayhealth.com  

Date: 11/06/2026  

Sunita Yadav  
l2, Oak Street, Hyderabad – 500001  

Subject: Claim Reference CLM-2026-5752299
IRDAI Regn. No. 000 | CIN: U66010MH2015PLC000000
– Decision Notification  

Dear Ms. Yadav,

We hope you are feeling better after your recent hospitalization at Lotus Care Hospital, Hyderabad, where you were admitted on 17/05/2026 for treatment of malaria. We sincerely appreciate the trust you have placed in Nirbhay Health Assurance and we are truly sorry for any inconvenience you may have
experienced during the claim process.

We have carefully reviewed the details of your claim under Policy No. NH/FLT/2026/641870. The amount claimed, Rs. 1,51,000, was duly received and examined. While we understand the importance of prompt support, we regret to inform you that as per the terms of your policy, the claim falls within the initial waiting period of 30 days from the start of the policy. Consequently, the expenses related to this admission are not eligible for reimbursement under the current policy provisions.

We sincerely apologise for any disappointment this decision may cause. Please be assured that our team is committed to providing you with clear information and assistance. If you have any questions or require further clarification, you may contact our Customer Care Desk at the above telephone number or email address. Should you wish to discuss this matter further, you may also submit a grievance through our grievance portal within 30 days of this letter.

Thank you for your understanding We value your association with Nirbhay Health Assurance and remain at your service for any future health coverage needs.

Yours sincerely,
Page 1 of 2

Senior Claims Officer  
Nirbhay Health Assurance (via CareBridge Health TPA)

POLICY DOCUMENT:
Nirbhay Health Assurance  
Policy Schedule – Individual Health Insurance  

Regd. Office: 4th Floor, Plot 12, Sector 9, Insurance Bhavan Marg
Policy Number: NH/FLT/2026/641870   Insured Person Sunita Yadav
Scanned with CamScanner

Date of first inception
(continuous cover since) 25/04/2026  
Sum Insured: Rs. 5,00,000  
Current Policy Period: 25/04/2026 to 24/04/2027  

Waiting Periods:  
• Initial waiting period – 30 days. This period is waived only
for accidents.  
• Specific diseases and procedures – 24 months.  
• Pre‑existing diseases – 36 months.  

Please note that the specific disease and pre‑existing disease waiting periods apply even when the treatment follows an accident. The policy provides coverage for hospitalisation, day‑care procedures and outpatient services as per the schedule, subject to the applicable waiting periods and other terms and conditions.  

For any queries or to
lodge a grievance, please contact our Customer Care at lB00‑123‑4S67 or email grievances@nirbhayhealth.com.

Return the JSON object.
```

**Label facts:** `{"policy_inception_date": "2026-04-25", "admission_date": "2026-05-17", "months_continuous_coverage": 0, "condition_named_by_insurer": "malaria", "waiting_period_months": 1, "is_accident": false, "accident_exempt_in_wording": false, "crc_approval_mentioned": false}`

**Reason:** The waiting period relied on is 1 months and the policy was 0 months old at admission, so the waiting period was not complete.

**Ask insurer for:** The exact policy clause relied on; Confirmation that the Claims Review Committee approved this repudiation

## 2. `train-0156`: no_hospitalisation_needed / short_stay -> **worth_asking**

Style: claim settlement advice with a small plain-text table of amounts, followed by remarks. Noisy: False.

```text
REJECTION LETTER:
Samriddhi Health Insurance  
Letter No.: 11/11/2025  

Date: 11/11/2025  

To,  
Ms. Geeta D'Souza  
Policy No.: SH/IND/2019/780392  
Claim No.: CLM-2025-9327307  

Hospital: Kaveri Speciality Hospital, Coimbatore  
Date of Admission: 17/09/2025 (admitted at 10:00 hrs)  
Date of Discharge: 17/09/2025 (discharged at 16:00 hrs)  
Diagnosis / Treatment: Management of a severe migraine attack  

Amount Claimed: INR 3,93,000  

**Settlement Table**  

Description                     | Claimed Amount | Payable Amount  
-------------------------------|----------------|---------------  
Hospitalisation Charges        | INR 3,93,000   | INR 0  
**Total**                       | INR 3,93,000   | INR 0  

**Remarks:**  

The claim has been reviewed by the Claims Review Committee and the decision to reject the hospitalisation component is final. The committee determined that the hospitalisation was not medically necessary, as the management of a severe migraine attack could have been provided on an outpatient (OPD) basis. Consequently, no amount is payable under the hospitalisation category.  

Please note that the policy has been in force with Samriddhi Health Insurance since 28/07/2023. Should you wish to appeal this decision, you may submit a written request within 30 days of receipt of this letter to the address below.  

For any further assistance, contact our Grievance Redressal Desk at grievance@samriddhihealth.in or call 1800-555-1234.  

Sincerely,  

__________________________  
Claims Manager  
Samriddhi Health Insurance

POLICY DOCUMENT:
Samriddhi Health Insurance  
Policy Schedule – Policy No.: SH/IND/2019/780392  

Insured: Geeta D'Souza  

Date of first inception / continuous cover since: 28/07/2019  
Policy with Samriddhi Health Insurance since: 28/07/2023  

Sum Insured: INR 10,00,000  

Current Policy Period: 28/07/2025 to 27/07/2026  

Room Rent Limit: INR 4,000 per day  

**Waiting Periods**  
- Initial waiting period: 30 days  
- Specific diseases and procedures: 24 months  
- Pre‑existing diseases: 48 months  

**Day care procedures covered (stay under 24 hours)**  
- Lithotripsy for a kidney stone  
- Arthroscopic knee surgery  
- A chemotherapy session  
- Tonsillectomy  

Address for correspondence:  
Samriddhi Health Insurance,  
Corporate Office, 12th Floor, Skyline Tower,  
Bangalore – 560001, India  

Grievance Contact: grievance@samriddhihealth.in | 1800-555-1234

Return the JSON object.
```

**Label facts:** `{"policy_inception_date": "2019-07-28", "admission_date": "2025-09-17", "months_continuous_coverage": 73, "is_accident": false, "hospital_stay_hours": 6, "is_listed_daycare_procedure": false, "room_rent_limit_per_day": 4000, "crc_approval_mentioned": true}`

**Reason:** With a 6-hour stay and no matching day care procedure in the policy, the rejection may hold. The treating doctor's justification could still change it.

**Ask insurer for:** The exact policy clause relied on; The medical opinion relied on to say hospitalisation was not needed

## 3. `train-0407`: non_disclosure_ped / disclosure_unknown -> **worth_asking**

Style: email from a claims executive, semi-formal, with a subject line and a signature block. Noisy: False.

```text
REJECTION LETTER:
Subject: Claim Rejection – Claim No. CLM-2024-9272691  

15-Aug-2024  

Mr. Prakash Joshi  
[Insured’s Address]  

Dear Mr. Joshi,

We refer to your claim under Policy No. SG/IND/2024/253669 for the hospitalization at Lotus Care Hospital, Hyderabad, dated 24-Jul-2024, for acute myocardial infarction with angioplasty. The amount claimed is ₹4,35,000 (Four Lakh Thirty‑Five Thousand Rupees).

After a detailed review of the claim documents and the medical records furnished by Lotus Care Hospital, we note that the hospital records indicate a documented history of coronary artery disease for a period of eleven (11) years prior to the commencement of your policy. As the policy requires full disclosure of any existing medical conditions, the non‑disclosure of this pre‑existing condition constitutes a breach of the proposal form requirements.

Consequently, we are unable to honour the claim in full. The amount payable under the policy for this admission is therefore reduced to zero, in accordance with the terms governing non‑disclosure of pre‑existing conditions.

If you wish to discuss this decision, please contact our Claims Helpline at 1800‑123‑4567 between 9:00 am and 6:00 pm on weekdays. You may also raise a grievance as per the Grievance Redressal Procedure outlined in your policy booklet.

Thank you for your understanding.

Yours sincerely,

Amit Sharma  
Claims Executive  
Suraksha General Insurance  
Email: claims@surakshainsurance.in  
Phone: 1800‑123‑4567

POLICY DOCUMENT:
Suraksha General Insurance – Policy Schedule  

Policy Number: SG/IND/2024/253669  
Insured: Prakash Joshi  

Date of first inception (continuous cover since): 24-Feb-2024  

Sum Insured: ₹15,00,000 (Fifteen Lakh Rupees)  

Current Policy Period: 24-Feb-2024 to 23-Feb-2025  

Room Rent Limit: ₹10,000 per day  

Waiting Periods:  
- Initial waiting period: 30 days from the date of policy commencement.  
- Specific diseases and procedures: 24 months waiting period before benefits become payable.  
- Pre‑existing diseases: 48 months waiting period before any benefit for such conditions may be considered.  

Coverage under this policy includes hospitalization expenses, including room rent up to the stated limit, intensive care unit charges, surgery fees, and post‑hospitalization care as per the policy wording. Day‑care procedures and diagnostic tests are covered subject to the applicable limits and waiting periods. The policy also provides a daily cash allowance for convalescence, subject to the terms outlined in the schedule.  

Exclusions are limited to those expressly mentioned in the policy document, and benefits are payable only when the claim meets all the conditions stipulated herein.  

For any queries regarding coverage, claim submission, or policy administration, please contact our Customer Service Centre at 1800‑123‑4567 or email support@surakshainsurance.in.

Return the JSON object.
```

**Label facts:** `{"policy_inception_date": "2024-02-24", "admission_date": "2024-07-24", "months_continuous_coverage": 5, "condition_named_by_insurer": "coronary artery disease", "condition_related_to_claim": true, "is_accident": false, "room_rent_limit_per_day": 10000, "crc_approval_mentioned": false}`

**Reason:** It is not possible to tell what was declared in the proposal form from these papers. Get that in writing before deciding whether to contest.

**Ask insurer for:** The exact policy clause relied on; Confirmation that the Claims Review Committee approved this repudiation; A copy of the proposal form that was signed

## 4. `train-0051`: non_disclosure_ped / valid -> **likely_valid**

Style: terse TPA claim denial note, short lines, almost no pleasantries. Noisy: True.

```text
REJECTION LETTER:
21/09/2024  
Samriddhi Health Insurance  
MediSetu TPA Services  

CONFIDENTIAL
To  
Ms. Kavita D'Souza  

Policy No.: SH/IND/2022/671252   Claim No.: CLM-2024-629127S

Hospital: Shanti Multispeciality Hospital, Pune   Date of Admission: 07/08/2024
Diagnosis / Treatment: acute
severe asthma exacerbation  

Claimed Amount: ₹114,O00  

Your claim is hereby rejected.  
The policy mandates disclosure of any pre‑existing condition. Hospital records indicate a bronchial asthma history of nine (9) years prior to the policy start date. No such condition was declared
in the proposal form.  
Scanned with CamScanner
As the condition is
classified as a pre‑existing disease and was not disclosed, the c1aim is not payable.  

For queries contact our grievance officer at grievance@samriddhihealth.in or call 1800‑123‑4567.

POLICY DOCUMENT:
Samriddhi Health Insurance  
Policy Schedule – Individual Health Cover  

Policy Number: SH/IND/2022/671252  
Insured: Kavita D'Souza   Date of First Inception (Continuous Cover Since): 02/09/2022

Sum Insured: ₹5,00,000  

Current Policy Period: 02/09/2023 to 01/09/2024  

Waiting Periods:  
- Initial waiting period: 30 days  
- Specific diseases and procedures:
24 months   - Pre‑existing diseases: 48 months

Pre‑existing diseases declared in proposal form: None declared.  

This schedule forms part of the policy wording and out1ines the coverage terms, exclusions, and conditions applicable during the policy period. The insurer reserves the right to amend terms as per regulatory guidelines.  

Toll free 1800 000 0000 | care@example.invalid
Toll free 1800 000 0000 | care@example.invalid
For any clarification write to:  
Samriddhi Health Insurance,  
Corporate Office, Mumbai – 400001, India.  
IRDAI Regn. No. 000 | CIN: U66010MH2015PLC000000

Authorized 5ignatory   Senior Underwriting Manager

Return the JSON object.
```

**Label facts:** `{"policy_inception_date": "2022-09-02", "admission_date": "2024-08-07", "months_continuous_coverage": 23, "condition_named_by_insurer": "bronchial asthma", "ped_disclosed_in_proposal": false, "condition_related_to_claim": true, "is_accident": false, "crc_approval_mentioned": false}`

**Reason:** With 23 months of continuous cover the moratorium does not apply, and the undeclared bronchial asthma is connected to this claim. This rejection is likely to stand.

**Ask insurer for:** The exact policy clause relied on; Confirmation that the Claims Review Committee approved this repudiation

## 5. `train-0076`: no_hospitalisation_needed / short_stay -> **worth_asking**

Style: terse TPA claim denial note, short lines, almost no pleasantries. Noisy: True.

```text
REJECTION LETTER:
Samriddhi Health Insurance
Letter Date: September 25, 2025

Page 1 of 2
Farida Chauhan
Policy No: SH/HLT/2021/867319
Toll free 1800 000 0000 | care@example.invalid
Claim No: CLM-2025-6315999

Hospital: Kaveri Speciality Hospital, Coimbatore Admission Date: September 4, 2025 Admitted at: 18:00 hrs Discharge Date: September 5, 2025
Discharged at: 16:00 hrs
Diagnosis/Treatment: IV antibiotics for urinary tract infection
Amount Claimed: Rs 1,59,00O

Rejection: Hospitalisation not medically necessary; same treatment could have
been provided on OPD basis.

No payment will be made on this claim.
For further information contact the claims desk at 1800‑123‑456.

POLICY DOCUMENT:
Samriddhi Health Insurance – Policy Schedule
Policy Number: SH/HLT/2021/867319
Insured: Farida Chauhan
Date of First Inception (continuous cover since): February 22, 2021 Sum Insured: Rs 3,00,000
Current Policy Period: February 22,
IRDAI Regn. No. 000 | CIN: U66010MH2015PLC000000
2025 to February 21, 2026
Room Rent Limit: Rs 10,000 per day

Waiting Periods
- Initial waiting period: 30 days
- Specific diseases and procedures: 24 months
- Pre‑existing diseases: 48 months

Day Care Procedures Covered (stay under 24 hours)
- A chemotherapy session
- Coronary angiography
- Cataract surgery (phacoemulsification)
- Tonsillectomy

Policy issued from Samriddhi Health Insurance, 12 Health Plaza Mumbai.
Authorized Signatory: Claims Operations Manager
Grievance Redressa1: grievances@samriddhihealth.in or call 1800‑987‑654

Return the JSON object.
```

**Label facts:** `{"policy_inception_date": "2021-02-22", "admission_date": "2025-09-04", "months_continuous_coverage": 54, "is_accident": false, "hospital_stay_hours": 22, "is_listed_daycare_procedure": false, "room_rent_limit_per_day": 10000, "crc_approval_mentioned": false}`

**Reason:** With a 22-hour stay and no matching day care procedure in the policy, the rejection may hold. The treating doctor's justification could still change it.

**Ask insurer for:** The exact policy clause relied on; Confirmation that the Claims Review Committee approved this repudiation; The medical opinion relied on to say hospitalisation was not needed

## 6. `train-0552`: waiting_period / accident_initial -> **likely_contestable**

Style: polite customer-care style letter that apologises a lot and buries the actual ground in the middle. Noisy: False.

```text
REJECTION LETTER:
Sanjeevani Bima Company  
Customer Care Department  
[Company Address]  

Date: 11.08.2021  

Mr. Anil Nair  
[Insured’s Address]  

Subject: Decision on Claim No. CLM-2021-1209448 – Policy No. SB/IND/2021/711557  

Dear Mr. Nair,

We hope this letter finds you well. First and foremost, we would like to express our sincere apologies for any inconvenience you may have experienced during the processing of your recent claim. We understand how distressing a forearm fracture can be, especially when it follows a fall from a ladder, and we appreciate the trust you placed in Sanjeevani Bima Company by seeking coverage for the treatment received at Sai Krupa Nursing Home, Nashik, on 25.06.2021.

Your claim for the amount of Rs. 5,07,000 has been carefully examined by our Claims Review Committee. After a thorough review of the policy terms and the particulars of the incident, the Committee has concluded that the claim falls within the initial waiting period of 30 days from the start of the policy. Consequently, under the applicable provisions, the claim cannot be honoured at this time.

Please be assured that this decision was reviewed and approved in accordance with our standard procedures by the insurer’s Claims Review Committee. We regret any disappointment this may cause and remain committed to assisting you with any future queries or claims.

If you wish to discuss this decision further, or if you have any other concerns, please do not hesitate to contact our grievance redressal team at grievance@sanjeevanibima.com or call 1800-123-456.

Thank you for your understanding.

Yours sincerely,

[Signature]  
Head of Claims  
Sanjeevani Bima Company

POLICY DOCUMENT:
Sanjeevani Bima Company – Policy Schedule  

Policy Number: SB/IND/2021/711557  
Insured: Anil Nair  

Date of First Inception (Continuous Cover Since): 18.06.2021  
Sum Insured: Rs. 5,00,000  
Current Policy Period: 18.06.2021 to 17.06.2022  

Waiting Periods  
- Initial Waiting Period: 30 days  
- Specific Diseases and Procedures: 24 months  
- Pre‑Existing Diseases: 48 months  

Coverage under this policy is subject to the terms, conditions, and exclusions set forth herein. The insured is required to disclose all material facts at the time of application and to adhere to the policy’s renewal and premium payment obligations. In the event of a claim, the insured must provide all necessary documentation and cooperate fully with the insurer’s investigation process.

For any queries regarding the policy wording, or to submit a grievance, please contact our customer service at 1800-123-456 or write to grievance@sanjeevanibima.com.

Return the JSON object.
```

**Label facts:** `{"policy_inception_date": "2021-06-18", "admission_date": "2021-06-25", "months_continuous_coverage": 0, "condition_named_by_insurer": "forearm fracture after a fall from a ladder", "waiting_period_months": 1, "is_accident": true, "crc_approval_mentioned": true}`

**Reason:** The hospitalisation followed an accident. The initial 30-day waiting period does not apply to accidents, so this rejection looks wrong.

**Ask insurer for:** The exact policy clause relied on

## 7. `train-0098`: documents_or_late_intimation / missing_documents -> **worth_asking**

Style: email from a claims executive, semi-formal, with a subject line and a signature block. Noisy: False.

```text
REJECTION LETTER:
Subject: Claim CLM-2025-7776090 – Closure Due to Non‑Submission of Documents  
Date: 08-Sep-2025  

Dear Imran Sharma,

Reference: Policy No. SG/HLT/2020/961100; Claim No. CLM-2025-7776090  

We refer to your claim for hospitalization at Shree Ganesh Hospital, Indore, with admission date 02-Aug-2025 for the treatment of kidney stones and an amount claimed of Rs. 3,70,000.  

Despite repeated reminders, we have not received the required documents, specifically the attending doctor’s certificate on duration of illness and the original discharge summary. Consequently, the claim is being closed for non‑submission of required documents.  

Please note that the claim is now considered closed and no payment will be made. Should you obtain the outstanding documents, you may submit a fresh claim in accordance with the terms of your policy.  

If you have any questions, you may contact our grievance cell via email at grievances@suraksha.com.  

Thank you for your understanding.  

Sincerely,  

Riya Patel  
Claims Executive  
Suraksha General Insurance  
Head Office, Mumbai

POLICY DOCUMENT:
Policy Schedule – Suraksha General Insurance  

Policy Number: SG/HLT/2020/961100  
Insured: Imran Sharma  
Date of First Inception (Continuous Cover Since): 07-Feb-2020  

Sum Insured: Rs. 15,00,000  

Current Policy Period: 07-Feb-2025 to 06-Feb-2026  

Room Rent Limit: Rs. 7,500 per day  

Waiting Periods:  
- Initial waiting period: 30 days  
- Specific diseases and procedures: 24 months  
- Pre‑existing diseases: 36 months  

The above schedule outlines the coverage limits, period of insurance and applicable waiting periods for the insured. The sum insured represents the maximum payable amount for a single claim arising from a covered event during the policy period. The room rent limit applies per day of hospitalization for rooms that are covered under the policy terms. The waiting periods are the minimum periods that must elapse from the inception date before benefits become available for the respective categories. Claims made before the expiry of the applicable waiting period will be subject to the terms and conditions of the policy.  

For any clarification or grievance, please write to grievances@suraksha.com.

Return the JSON object.
```

**Label facts:** `{"policy_inception_date": "2020-02-07", "admission_date": "2025-08-02", "months_continuous_coverage": 65, "is_accident": false, "room_rent_limit_per_day": 7500, "crc_approval_mentioned": false}`

**Reason:** This is a procedural rejection. Send the pending documents or a written explanation for the delay and ask for the claim to be reopened.

**Ask insurer for:** The exact policy clause relied on; Confirmation that the Claims Review Committee approved this repudiation; The exact list of documents still pending

## 8. `eval_synth-0049`: other / treatment_protocol -> **worth_asking**

Style: two-part document: a three-line SMS-style alert, then a formal annexure headed 'Reasons for decision'. Noisy: True.

```text
REJECTION LETTER:
Dhanraksha General Insurance - Claim Update
C1aim No: CLM-2025-1027762
Decision Not Payable

Reasons for decision
Date: 12 April 2025
Dear Mr. Devendra Sharma,
Policy No.: DG/HLT/2021/747267

We have reviewed your claim (Claim No.: CLM-2025-1027762) for hospitalization at Kaveri Speciality Hospital, Coimbatore, admission date 4 February 2025, diagnosed with typhoid fever, and the amount claimed of Rs 2,30,000. The claim was processed through our TPA, CareBridge Health TPA. After assessment, it has been determined that the line of treatment and the length of stay are not consistent with the standard treatment protocols applicable to typhoid
fever. Consequently, the claim is not payable under the terms of your policy.

IRDAI Regn. No. 000 | CIN: U66010MH2015PLC000000
If you require further clarification, please contact our grievance cell at 1800-XXXX-XXXX.

Sincerely,
Senior Claims Officer
Regd. Office: 4th Floor, Plot 12, Sector 9, Insurance Bhavan Marg
Dhanraksha General Insurance
Scanned with CamScanner

POLICY DOCUMENT:
Policy Schedule – Dhanraksha General Insurance
Policy Number: DG/HLT/2021/747267
Insured: Devendra Sharma
Date of first inception (continuous cover since):
22 April 2021
Sum Insured: Rs 15,00,000
CONFIDENTIAL
Current Policy Period: 22 April 2024 to 21 April 2025

Coverage
The policy provides health insurance cover for hospitalization, day care procedures, and related medical expenses
as per the terms and conditions of the policy contract.

Waiting Periods
- Initial waiting period: 30 days from the date of commencement of the policy.
- Specific diseases and procedures: 24 months waiting period.
- Pre‑existing diseases 36 months waiting period.

General Conditions
The insured is required to seek treatment at network hospitals where possible, and to submit all relevant medical documents
for claim processing. The policy does not impose any specific room rent limits or room category entitlements.

For any queries or to
lodge a grievance, please contact our Grievance Redressal Cell at 1800-XXXX-XXXX or email grievance@dhanraksha.com.

Dhanraksha General Insurance
Head Office – 123 Insurance
Avenue Mumbai – 400O01
Authorized Signatory
Chief Underwriting Officer

Return the JSON object.
```

**Label facts:** `{"policy_inception_date": "2021-04-22", "admission_date": "2025-02-04", "months_continuous_coverage": 45, "is_accident": false, "crc_approval_mentioned": false}`

**Reason:** It is not clear from the documents whether this rejection is right. Ask for the clause and the basis of the decision.

**Ask insurer for:** The exact policy clause relied on; Confirmation that the Claims Review Committee approved this repudiation

## 9. `eval_synth-0077`: documents_or_late_intimation / missing_documents -> **worth_asking**

Style: claim status printout from a customer portal: mostly 'Field: value' lines and a free-text 'Remarks' box. Noisy: False.

```text
REJECTION LETTER:
Issuer: Samriddhi Health Insurance
Letter Date: 01-Sep-2022
Insured Name: Harpreet Chauhan
Policy Number: SH/FLT/2020/821565
Claim Number: CLM-2022-8655950
Hospital Name: Sai Krupa Nursing Home, Nashik
Date of Admission: 20-Jul-2022
Diagnosis/Treatment: inguinal hernia
Amount Claimed: INR 1,60,000
Claim Status: Rejected
Reason for Rejection: Claim closed for non‑submission of required documents despite reminders.
Documents Not Received: KYC documents of the proposer; indoor case papers.
Decision Review: Decision reviewed and approved by Claims Review Committee
Remarks: Your claim has been closed as the required documents were not received despite multiple reminders. The decision has been reviewed and approved by the insurer’s Claims Review Committee. Please contact our customer service for further assistance.

POLICY DOCUMENT:
Policy Schedule
Policy Number: SH/FLT/2020/821565
Insured: Harpreet Chauhan
Date of First Inception (Continuous Cover Since): 30-Nov-2020
Sum Insured: INR 5,00,000
Current Policy Period: 28-Nov-2021 to 27-Nov-2022

Policy Wording
This policy provides health insurance coverage as per the terms and conditions set forth herein. Benefits are payable subject to the policy schedule and the applicable waiting periods. The policy is issued by Samriddhi Health Insurance and remains in force for the current policy period unless terminated in accordance with policy provisions.

Waiting Periods
Initial waiting period: 30 days.
Specific diseases and procedures: 24 months.
Pre‑existing diseases: 36 months.

The policyholder may contact the grievance redressal cell at grievance@samriddhihealth.com or call 1800‑123‑4567 for any disputes. The policy is governed by the laws of India.

Signed,
Authorized Signatory
Samriddhi Health Insurance
123 Health Avenue, Mumbai, India

Return the JSON object.
```

**Label facts:** `{"policy_inception_date": "2020-11-30", "admission_date": "2022-07-20", "months_continuous_coverage": 19, "is_accident": false, "crc_approval_mentioned": true}`

**Reason:** This is a procedural rejection. Send the pending documents or a written explanation for the delay and ask for the claim to be reopened.

**Ask insurer for:** The exact policy clause relied on; The exact list of documents still pending

## 10. `eval_synth-0008`: waiting_period / accident_wording_unknown -> **worth_asking**

Style: claim status printout from a customer portal: mostly 'Field: value' lines and a free-text 'Remarks' box. Noisy: False.

```text
REJECTION LETTER:
Insurer: Suraksha General Insurance
Letter Date: 29.11.2022
Insured Name: Ramesh Kulkarni
Policy Number: SG/HLT/2020/147436
Claim Number: CLM-2022-9825305
Hospital Name: Shree Ganesh Hospital, Indore
Date of Admission: 21.09.2022
Diagnosis / Treatment: Traumatic cataract after a road traffic accident
Amount Claimed: INR 2,72,000
Status: Rejected
Remarks:
The claim has been examined against the terms of your health insurance contract. Although the cataract surgery was required following a road traffic accident, the policy provision for specific diseases imposes a waiting period of twenty‑four (24) months for cataract. The date of admission falls within this specific disease waiting period. Consequently, the claim amount of INR 2,72,000 is not payable under the policy. For any further clarification, you may contact our grievance cell at grievance@surakshainsurance.in or call 1800‑123‑4567.

POLICY DOCUMENT:
Suraksha General Insurance
Policy Schedule – Health Insurance

Policy Number: SG/HLT/2020/147436
Insured: Ramesh Kulkarni
Date of First Inception (Continuous Cover Since): 31.10.2020
Sum Insured: INR 10,00,000
Current Policy Period: 28.10.2021 to 27.10.2022

Waiting Periods:
- Initial Waiting Period: 30 days from the date of policy commencement.
- Specific Diseases and Procedures: 24 months waiting period applies to designated conditions, including cataract.
- Pre‑Existing Diseases: 36 months waiting period applies to any condition diagnosed before the policy start date.

This schedule forms part of the contract of insurance between the insurer and the insured. The terms and conditions set out herein are binding upon acceptance of the policy. For any queries regarding coverage, please refer to the policy handbook or contact our customer service desk.

Grievance Contact: grievance@surakshainsurance.in | 1800‑123‑4567
Signatory: Senior Manager – Claims & Underwriting

Return the JSON object.
```

**Label facts:** `{"policy_inception_date": "2020-10-31", "admission_date": "2022-09-21", "months_continuous_coverage": 22, "condition_named_by_insurer": "cataract", "waiting_period_months": 24, "is_accident": true, "crc_approval_mentioned": false}`

**Reason:** Neither the letter nor the policy excerpt shows whether the policy wording exempts accidents from the 24-month waiting period. Ask for it.

**Ask insurer for:** The exact policy clause relied on; Confirmation that the Claims Review Committee approved this repudiation; Whether the policy wording exempts accidents from this waiting period, with the clause
