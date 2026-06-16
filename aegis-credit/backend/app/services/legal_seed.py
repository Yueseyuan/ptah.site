"""Seed functions for the Legal Knowledge Engine."""
from __future__ import annotations


def seed_federal_laws(db):
    """Seed federal laws if the table is empty."""
    from app.models import FederalLaw

    if db.query(FederalLaw).count() > 0:
        return

    laws = [
        # FCRA key sections
        {
            "short_name": "FCRA",
            "title": "Fair Credit Reporting Act",
            "citation": "15 U.S.C. § 1681 et seq.",
            "section": "§605(a)",
            "summary": (
                "Restricts the reporting of obsolete adverse information. "
                "Most negative items may not be reported after 7 years from the date of first delinquency. "
                "Bankruptcies may be reported for up to 10 years. "
                "Certain items such as criminal convictions, credit transactions over $150,000, and life "
                "insurance policies over $150,000 are exempt from these time limits."
            ),
            "effective_date": "1971-04-25",
            "category": "credit_reporting",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act",
        },
        {
            "short_name": "FCRA",
            "title": "Fair Credit Reporting Act",
            "citation": "15 U.S.C. § 1681 et seq.",
            "section": "§611",
            "summary": (
                "Requires consumer reporting agencies (CRAs) to investigate disputes filed by consumers. "
                "CRAs must complete investigations within 30 days (45 days if the consumer provides "
                "additional information during the dispute period). "
                "If the disputed information is found to be inaccurate, incomplete, or unverifiable, "
                "the CRA must delete or correct it. The furnisher must also investigate and correct "
                "any inaccurate information reported to the CRA."
            ),
            "effective_date": "1971-04-25",
            "category": "credit_reporting",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act",
        },
        {
            "short_name": "FCRA",
            "title": "Fair Credit Reporting Act",
            "citation": "15 U.S.C. § 1681 et seq.",
            "section": "§612",
            "summary": (
                "Entitles consumers to free disclosure of their credit file upon request once every 12 months. "
                "Consumers are also entitled to a free report when: adverse action is taken based on the report, "
                "the consumer is unemployed and plans to apply for employment, the consumer is on public welfare "
                "assistance, or the consumer has reason to believe the file contains inaccurate information "
                "due to fraud. CRAs must also provide free scores with certain disclosures."
            ),
            "effective_date": "1971-04-25",
            "category": "credit_reporting",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act",
        },
        {
            "short_name": "FCRA",
            "title": "Fair Credit Reporting Act",
            "citation": "15 U.S.C. § 1681 et seq.",
            "section": "§623",
            "summary": (
                "Imposes accuracy requirements on furnishers of information to CRAs. "
                "Furnishers must not report information they know or have reasonable cause to believe is "
                "inaccurate. After receiving notice of a dispute from a CRA, furnishers must investigate "
                "and report results back to the CRA. Furnishers must also correct and update information "
                "that is determined to be inaccurate. Consumers may dispute information directly with "
                "furnishers under certain circumstances."
            ),
            "effective_date": "1971-04-25",
            "category": "credit_reporting",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act",
        },
        # FDCPA
        {
            "short_name": "FDCPA",
            "title": "Fair Debt Collection Practices Act",
            "citation": "15 U.S.C. § 1692 et seq.",
            "section": "§1692 et seq.",
            "summary": (
                "Prohibits abusive, unfair, and deceptive practices by debt collectors. "
                "Debt collectors may not harass, oppress, or abuse consumers. "
                "They must identify themselves, disclose the debt, and provide validation notices. "
                "Consumers have the right to dispute debts and request verification. "
                "Debt collectors are prohibited from communicating with consumers at unusual times "
                "or places, or after the consumer requests cessation of communication."
            ),
            "effective_date": "1978-03-20",
            "category": "debt_collection",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-debt-collection-practices-act",
        },
        # CROA
        {
            "short_name": "CROA",
            "title": "Credit Repair Organizations Act",
            "citation": "15 U.S.C. § 1679 et seq.",
            "section": "§1679 et seq.",
            "summary": (
                "Regulates credit repair organizations. Prohibits credit repair organizations from "
                "making false or misleading representations. Requires written contracts, a 3-day "
                "cancellation right, and prohibits advance fees for services. Organizations cannot "
                "advise consumers to make false statements to credit bureaus or lenders. "
                "Consumers have private rights of action for violations."
            ),
            "effective_date": "1996-04-01",
            "category": "credit_repair",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/credit-repair-organizations-act",
        },
        # ECOA
        {
            "short_name": "ECOA",
            "title": "Equal Credit Opportunity Act",
            "citation": "15 U.S.C. § 1691 et seq.",
            "section": "§1691 et seq.",
            "summary": (
                "Prohibits discrimination in credit transactions on the basis of race, color, religion, "
                "national origin, sex, marital status, age, or receipt of public assistance. "
                "Creditors must notify applicants of adverse action within 30 days and provide specific "
                "reasons for denial. The CFPB and DOJ enforce ECOA. Consumers have a private right of "
                "action for violations."
            ),
            "effective_date": "1975-10-28",
            "category": "lending",
            "source_url": "https://www.consumerfinance.gov/compliance/compliance-resources/other-applicable-requirements/equal-credit-opportunity-act/",
        },
        # TILA
        {
            "short_name": "TILA",
            "title": "Truth in Lending Act",
            "citation": "15 U.S.C. § 1601 et seq.",
            "section": "§1601 et seq.",
            "summary": (
                "Requires clear disclosure of key terms of the lending arrangement and all costs. "
                "Lenders must disclose the annual percentage rate (APR), finance charges, amount financed, "
                "total payments, and payment schedule. Consumers have a right of rescission on certain "
                "mortgage transactions. TILA also governs credit card disclosures, billing error "
                "resolution, and protections against unauthorized use."
            ),
            "effective_date": "1969-07-01",
            "category": "lending",
            "source_url": "https://www.consumerfinance.gov/compliance/compliance-resources/mortgage-resources/tila-respa-integrated-disclosures/",
        },
        # FACTA
        {
            "short_name": "FACTA",
            "title": "Fair and Accurate Credit Transactions Act",
            "citation": "Pub. L. 108-159 (amends FCRA)",
            "section": "Various amendments to FCRA",
            "summary": (
                "Amended the FCRA to add significant consumer protections. Key provisions include: "
                "free annual credit reports from each major bureau, fraud alerts and active duty alerts, "
                "blocking of information resulting from identity theft, truncation of credit card numbers "
                "on receipts, enhanced accuracy and dispute procedures, and the Red Flags Rule requiring "
                "creditors to implement identity theft prevention programs. "
                "FACTA also created the CFPB's authority over fair credit reporting."
            ),
            "effective_date": "2004-12-04",
            "category": "credit_reporting",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act",
        },
        # GLBA
        {
            "short_name": "GLBA",
            "title": "Gramm-Leach-Bliley Act",
            "citation": "15 U.S.C. § 6801 et seq.",
            "section": "§6801 et seq.",
            "summary": (
                "Requires financial institutions to protect consumers' private financial information. "
                "Financial institutions must provide privacy notices explaining their information-sharing "
                "practices and allow consumers to opt out of sharing with non-affiliated third parties. "
                "The Safeguards Rule requires financial institutions to implement information security "
                "programs. The Pretexting Protection provisions prohibit the use of false pretenses to "
                "obtain financial information."
            ),
            "effective_date": "2001-07-01",
            "category": "privacy",
            "source_url": "https://www.ftc.gov/business-guidance/privacy-security/gramm-leach-bliley-act",
        },
        # Regulation V
        {
            "short_name": "Reg V",
            "title": "Regulation V — Fair Credit Reporting",
            "citation": "12 C.F.R. § 1022 et seq.",
            "section": "§1022 et seq.",
            "summary": (
                "CFPB regulation implementing the FCRA. Establishes requirements for consumer reporting "
                "agencies and furnishers of information. Includes the Risk-Based Pricing Rule (requiring "
                "notice when less favorable credit terms are offered based on a credit report), "
                "the Affiliate Marketing Rule, and the Address Discrepancy Rule. "
                "Regulation V also contains the model forms for adverse action notices and other "
                "required disclosures under the FCRA."
            ),
            "effective_date": "2011-07-21",
            "category": "credit_reporting",
            "source_url": "https://www.consumerfinance.gov/rules-policy/final-rules/regulation-v-fair-credit-reporting-act/",
        },
    ]

    for law_data in laws:
        law = FederalLaw(**law_data)
        db.add(law)
    db.commit()


def seed_agency_guidance(db):
    """Seed CFPB/FTC agency guidance if the table is empty."""
    from app.models import AgencyGuidance

    if db.query(AgencyGuidance).count() > 0:
        return

    guidance_records = [
        {
            "agency": "CFPB",
            "document_name": "FCRA Model Summary of Rights",
            "publication_date": "2018-09-01",
            "topic": "Consumer Rights Under FCRA",
            "summary": (
                "The CFPB's model summary of consumer rights under the Fair Credit Reporting Act. "
                "Describes rights to access credit reports, dispute inaccurate information, "
                "place fraud alerts and security freezes, and seek remedies for violations. "
                "CRAs are required to provide this summary to consumers upon request or when "
                "taking adverse action based on a consumer report."
            ),
            "source_url": "https://www.consumerfinance.gov/consumer-tools/credit-reports-and-scores/",
        },
        {
            "agency": "CFPB",
            "document_name": "Supervisory Guidance on Credit Reporting Accuracy",
            "publication_date": "2013-07-10",
            "topic": "Furnisher Accuracy Requirements",
            "summary": (
                "CFPB supervisory guidance for financial institutions that furnish information to "
                "consumer reporting agencies. Addresses the accuracy requirements under FCRA §623, "
                "including reasonable policies and procedures to ensure accuracy, investigations of "
                "consumer disputes, and correction of errors. Guidance emphasizes that furnishers "
                "bear responsibility for the accuracy of the information they report."
            ),
            "source_url": "https://www.consumerfinance.gov/compliance/supervision-examinations/",
        },
        {
            "agency": "CFPB",
            "document_name": "Fair Credit Reporting Act Examination Procedures",
            "publication_date": "2012-10-01",
            "topic": "FCRA Examination Procedures",
            "summary": (
                "CFPB examination procedures for evaluating compliance with the Fair Credit Reporting "
                "Act. Covers CRA obligations, furnisher obligations, user obligations, and requirements "
                "for consumer disclosures, dispute handling, and adverse action notices. Used by CFPB "
                "examiners to assess whether supervised entities are complying with FCRA requirements."
            ),
            "source_url": "https://www.consumerfinance.gov/compliance/supervision-examinations/",
        },
        {
            "agency": "FTC",
            "document_name": "40 Years of Experience with the Fair Credit Reporting Act",
            "publication_date": "2011-07-01",
            "topic": "FCRA History and Enforcement",
            "summary": (
                "FTC staff report examining 40 years of FCRA enforcement and interpretation. "
                "Provides analysis of the FTC's historical interpretation of FCRA provisions, "
                "including coverage of different types of consumer reports, permissible purposes, "
                "accuracy requirements, and identity theft protections. "
                "Useful reference for understanding how the FTC has applied FCRA in practice."
            ),
            "source_url": "https://www.ftc.gov/reports/40-years-experience-fair-credit-reporting-act-ftc-staff-report-summary-interpretations",
        },
        {
            "agency": "CFPB",
            "document_name": "Credit Reporting Complaints Annual Report",
            "publication_date": "2023-03-01",
            "topic": "Credit Reporting Complaint Trends",
            "summary": (
                "Annual CFPB report analyzing consumer complaints about credit reporting. "
                "Identifies common complaint categories including incorrect information, problems "
                "with investigation responses, improper use of credit reports, and issues with "
                "credit monitoring services. Data used to prioritize supervisory and enforcement "
                "activities. Key resource for understanding systemic issues in credit reporting."
            ),
            "source_url": "https://www.consumerfinance.gov/data-research/research-reports/",
        },
    ]

    for g in guidance_records:
        doc = AgencyGuidance(**g)
        db.add(doc)
    db.commit()


def seed_case_law(db):
    """Seed landmark FCRA/FDCPA cases if the table is empty."""
    from app.models import CaseLaw
    import json

    if db.query(CaseLaw).count() > 0:
        return

    cases = [
        {
            "case_name": "Spokeo, Inc. v. Robins",
            "citation": "578 U.S. 330 (2016)",
            "court": "U.S. Supreme Court",
            "jurisdiction": "Federal",
            "year": 2016,
            "topic": "FCRA Standing / Statutory Damages",
            "holding_summary": (
                "A plaintiff cannot satisfy Article III standing merely by alleging a statutory "
                "violation of the FCRA without showing a concrete injury. The injury-in-fact "
                "requirement demands a concrete and particularized harm, not just a risk of harm. "
                "However, intangible injuries can be concrete if they have a 'close relationship' "
                "to harms traditionally recognized in law."
            ),
            "legal_principle": (
                "Article III standing requires a concrete injury even for statutory violations. "
                "Bare procedural violations of the FCRA do not automatically confer standing."
            ),
            "relevance_tags": json.dumps(["standing", "statutory damages", "FCRA", "Article III"]),
            "source_url": "https://www.supremecourt.gov/opinions/15pdf/13-1339_0pm1.pdf",
        },
        {
            "case_name": "Safeco Insurance Co. of America v. Burr",
            "citation": "551 U.S. 47 (2007)",
            "court": "U.S. Supreme Court",
            "jurisdiction": "Federal",
            "year": 2007,
            "topic": "FCRA Willfulness Standard",
            "holding_summary": (
                "Defined the 'willful' standard under FCRA §616 for statutory and punitive damages. "
                "A company acts willfully if it acts in 'reckless disregard' of a consumer's FCRA "
                "rights. Objective unreasonableness can satisfy willfulness; subjective bad faith is "
                "not required. An objectively reasonable interpretation of the statute defeats willfulness."
            ),
            "legal_principle": (
                "Willful FCRA violations include reckless disregard of consumer rights, not just "
                "knowing violations. The standard is objective unreasonableness."
            ),
            "relevance_tags": json.dumps(["willfulness", "punitive damages", "adverse action", "FCRA §616"]),
            "source_url": "https://www.supremecourt.gov/opinions/06pdf/06-84.pdf",
        },
        {
            "case_name": "Gorman v. Wolpoff & Abramson, LLP",
            "citation": "584 F.3d 1147 (9th Cir. 2009)",
            "court": "U.S. Court of Appeals, Ninth Circuit",
            "jurisdiction": "9th Circuit",
            "year": 2009,
            "topic": "FCRA Furnisher Dispute Investigation",
            "holding_summary": (
                "Addressed the reasonableness of a furnisher's reinvestigation under FCRA §623(b). "
                "The court held that furnishers must conduct a meaningful investigation of consumer "
                "disputes, not merely a perfunctory review of their own records. A furnisher that "
                "simply checks its own records without considering evidence provided by the consumer "
                "may not satisfy the reasonable reinvestigation requirement."
            ),
            "legal_principle": (
                "Furnishers must conduct reasonable reinvestigations of consumer disputes under FCRA "
                "§623(b). Mere reliance on internal records without considering consumer-provided "
                "evidence is insufficient."
            ),
            "relevance_tags": json.dumps(["furnisher", "reinvestigation", "FCRA §623", "dispute"]),
            "source_url": "https://law.justia.com/cases/federal/appellate-courts/ca9/07-16942/07-16942-2010-05-10.html",
        },
        {
            "case_name": "Reardon v. Closetmaid Corp.",
            "citation": "2013 WL 6231606 (W.D. Pa. 2013)",
            "court": "U.S. District Court, W.D. Pennsylvania",
            "jurisdiction": "3rd Circuit",
            "year": 2013,
            "topic": "FCRA Pre-Adverse Action Procedure",
            "holding_summary": (
                "Addressed employer obligations when using consumer reports for employment decisions. "
                "The court found that an employer violated FCRA §604(b) by failing to provide a "
                "copy of the consumer report and a summary of consumer rights before taking adverse "
                "action. The pre-adverse action procedure must be followed before an adverse "
                "employment decision is made, not simultaneously with or after the decision."
            ),
            "legal_principle": (
                "Employers must provide pre-adverse action disclosure (copy of report and Summary of "
                "Rights) before making an adverse employment decision based on a consumer report."
            ),
            "relevance_tags": json.dumps(["employment", "adverse action", "FCRA §604(b)", "pre-adverse action"]),
            "source_url": "https://law.justia.com/cases/federal/district-courts/pennsylvania/pawdce/2:2010cv01730/104048/250/",
        },
        {
            "case_name": "Cahlin v. General Motors Acceptance Corp.",
            "citation": "936 F.2d 1151 (11th Cir. 1991)",
            "court": "U.S. Court of Appeals, Eleventh Circuit",
            "jurisdiction": "11th Circuit",
            "year": 1991,
            "topic": "FCRA CRA Reinvestigation Duty",
            "holding_summary": (
                "Established that a consumer reporting agency has a duty to conduct a reasonable "
                "reinvestigation when a consumer disputes the accuracy of information in their credit "
                "file under FCRA §611. The CRA cannot simply verify information by asking the "
                "original furnisher to confirm it. The reinvestigation must be sufficient to "
                "determine whether the dispute has merit. Negligent noncompliance allows actual "
                "damages recovery."
            ),
            "legal_principle": (
                "CRAs must conduct reasonable reinvestigations of consumer disputes. Simply "
                "reconfirming information with the original furnisher is insufficient. "
                "Negligent violations permit actual damages."
            ),
            "relevance_tags": json.dumps(["CRA", "reinvestigation", "FCRA §611", "negligence", "actual damages"]),
            "source_url": "https://law.justia.com/cases/federal/appellate-courts/F2/936/1151/47617/",
        },
    ]

    for c in cases:
        case = CaseLaw(**c)
        db.add(case)
    db.commit()
