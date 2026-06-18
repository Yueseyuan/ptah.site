"""Seed functions for the Legal Knowledge Engine."""
from __future__ import annotations


def seed_federal_laws(db):
    """Upsert federal laws (keyed on citation+section)."""
    from app.models import FederalLaw

    laws = [
        # ── FCRA ──────────────────────────────────────────────────────────────
        {
            "short_name": "FCRA",
            "title": "Fair Credit Reporting Act",
            "citation": "15 U.S.C. § 1681 et seq.",
            "section": "§604",
            "summary": (
                "Limits the permissible purposes for which a consumer report may be obtained. "
                "A consumer report may only be furnished for: credit or insurance transactions "
                "initiated by the consumer, employment purposes (with written consent), "
                "legitimate business needs in a transaction initiated by the consumer, "
                "court orders or subpoenas, and child-support enforcement. "
                "Users who obtain reports under false pretenses may face criminal liability under §619."
            ),
            "effective_date": "1971-04-25",
            "category": "credit_reporting",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act",
        },
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
            "section": "§605B",
            "summary": (
                "Requires consumer reporting agencies to block the reporting of information the consumer "
                "identifies as resulting from identity theft. Upon receiving a valid identity-theft report "
                "and proof of identity, the CRA must block the information within 4 business days and "
                "notify the furnisher. The CRA may decline or rescind the block if it determines the "
                "information was not the result of identity theft. Furnishers must also be notified and "
                "may not re-furnish the blocked information."
            ),
            "effective_date": "2004-12-04",
            "category": "credit_reporting",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act",
        },
        {
            "short_name": "FCRA",
            "title": "Fair Credit Reporting Act",
            "citation": "15 U.S.C. § 1681 et seq.",
            "section": "§609",
            "summary": (
                "Requires consumer reporting agencies to disclose to the consumer, on request, "
                "all information in the consumer's file at the time of the request, the sources of "
                "the information, and the identity of each person that procured a consumer report for "
                "employment purposes within the preceding 2-year period, or for any other purpose "
                "within the preceding 1-year period. "
                "The CRA must also provide a summary of rights and a written statement of dispute "
                "procedures if the consumer disputes the accuracy of any item."
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
            "section": "§613",
            "summary": (
                "Governs the reporting of public-record information (e.g., bankruptcies, judgments, tax liens, "
                "and arrest records) to consumer reporting agencies. "
                "CRAs that compile and report public-record information must either: "
                "(1) notify the consumer at the time the information is reported, or "
                "(2) maintain strict procedures to ensure the information is complete and up to date. "
                "This section is particularly relevant when public records are outdated, expunged, or sealed."
            ),
            "effective_date": "1971-04-25",
            "category": "credit_reporting",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act",
        },
        {
            "short_name": "FCRA",
            "title": "Fair Credit Reporting Act",
            "citation": "15 U.S.C. § 1681 et seq.",
            "section": "§615",
            "summary": (
                "Imposes requirements on users of consumer reports who take adverse action. "
                "When a person takes adverse action based in whole or in part on a consumer report, "
                "they must: (1) notify the consumer of the adverse action, (2) provide the name, "
                "address, and phone number of the CRA that furnished the report, (3) state that the "
                "CRA did not make the decision and cannot explain it, and (4) inform the consumer of "
                "their right to obtain a free copy of the report and to dispute its accuracy. "
                "Failure to provide adverse action notices is a common FCRA violation."
            ),
            "effective_date": "1971-04-25",
            "category": "credit_reporting",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act",
        },
        {
            "short_name": "FCRA",
            "title": "Fair Credit Reporting Act",
            "citation": "15 U.S.C. § 1681 et seq.",
            "section": "§616",
            "summary": (
                "Provides civil liability for willful noncompliance with the FCRA. "
                "Any person who willfully fails to comply with any requirement of the FCRA is liable "
                "to the consumer for: (1) actual damages or statutory damages of $100–$1,000 per violation, "
                "(2) punitive damages as the court may allow, and (3) attorney fees and costs. "
                "The 'willful' standard includes reckless disregard of the consumer's FCRA rights "
                "(see Safeco Insurance Co. v. Burr, 551 U.S. 47 (2007))."
            ),
            "effective_date": "1971-04-25",
            "category": "credit_reporting",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act",
        },
        {
            "short_name": "FCRA",
            "title": "Fair Credit Reporting Act",
            "citation": "15 U.S.C. § 1681 et seq.",
            "section": "§617",
            "summary": (
                "Provides civil liability for negligent noncompliance with the FCRA. "
                "Any person who negligently fails to comply with any requirement of the FCRA "
                "is liable to the consumer for: (1) actual damages sustained, and "
                "(2) attorney fees and costs. Unlike §616 (willful violations), §617 does not "
                "allow statutory or punitive damages — the consumer must prove actual harm. "
                "Common negligent violations include failure to reinvestigate disputes within "
                "the required 30-day period and failure to delete unverifiable information."
            ),
            "effective_date": "1971-04-25",
            "category": "credit_reporting",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act",
        },
        {
            "short_name": "FCRA",
            "title": "Fair Credit Reporting Act",
            "citation": "15 U.S.C. § 1681 et seq.",
            "section": "§619",
            "summary": (
                "Criminalizes obtaining a consumer report under false pretenses. "
                "Any person who knowingly and willfully obtains information on a consumer from a "
                "consumer reporting agency under false pretenses is subject to a fine and/or "
                "imprisonment for up to 2 years. Officers and employees of CRAs who knowingly "
                "disclose consumer report information to unauthorized persons face similar penalties. "
                "This section reinforces the permissible purpose requirements of §604."
            ),
            "effective_date": "1971-04-25",
            "category": "credit_reporting",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act",
        },
        {
            "short_name": "FCRA",
            "title": "Fair Credit Reporting Act",
            "citation": "15 U.S.C. § 1681 et seq.",
            "section": "§620",
            "summary": (
                "Prohibits unauthorized disclosures by officers or employees of consumer reporting agencies. "
                "Officers, employees, and contractors of CRAs who knowingly and willfully provide "
                "consumer report information to an unauthorized person may be fined and/or imprisoned "
                "for up to 2 years. This section works in conjunction with §604 (permissible purposes) "
                "and §619 (obtaining information under false pretenses) to protect consumer privacy."
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
        {
            "short_name": "FCRA",
            "title": "Fair Credit Reporting Act",
            "citation": "15 U.S.C. § 1681 et seq.",
            "section": "§625",
            "summary": (
                "Establishes the relationship between the FCRA and state laws. "
                "The FCRA generally preempts state laws that impose inconsistent requirements on "
                "consumer reporting agencies and furnishers of information — however, states may enact "
                "laws that provide greater protections for consumers. "
                "Key exceptions: states may regulate consumer reporting to the extent not preempted, "
                "and the FCRA specifically preserves state laws relating to the obligations of "
                "furnishers, adverse action procedures, and identity theft protections."
            ),
            "effective_date": "1996-09-30",
            "category": "credit_reporting",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-credit-reporting-act",
        },
        # ── FDCPA ─────────────────────────────────────────────────────────────
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
        {
            "short_name": "FDCPA",
            "title": "Fair Debt Collection Practices Act",
            "citation": "15 U.S.C. § 1692 et seq.",
            "section": "§1692c",
            "summary": (
                "Restricts communication by debt collectors. Collectors may not contact consumers "
                "at unusual times (before 8 a.m. or after 9 p.m.), at a place of employment if the "
                "collector knows the employer prohibits such calls, or directly with a consumer who "
                "is represented by an attorney. If the consumer notifies the collector in writing to "
                "cease communication, the collector must stop all contact except to notify the consumer "
                "of specific actions (e.g., filing a lawsuit). Third-party communication is also "
                "sharply limited — collectors may only contact third parties to locate the consumer."
            ),
            "effective_date": "1978-03-20",
            "category": "debt_collection",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-debt-collection-practices-act",
        },
        {
            "short_name": "FDCPA",
            "title": "Fair Debt Collection Practices Act",
            "citation": "15 U.S.C. § 1692 et seq.",
            "section": "§1692d",
            "summary": (
                "Prohibits harassment, oppression, and abuse by debt collectors. "
                "Specifically bars: threatening violence or harm, using obscene or profane language, "
                "publishing a list of consumers who refuse to pay debts, advertising the debt for sale "
                "to coerce payment, causing the telephone to ring repeatedly to annoy the consumer, "
                "and failing to disclose identity when placing a telephone call. "
                "Each harassing act or communication may constitute a separate violation."
            ),
            "effective_date": "1978-03-20",
            "category": "debt_collection",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-debt-collection-practices-act",
        },
        {
            "short_name": "FDCPA",
            "title": "Fair Debt Collection Practices Act",
            "citation": "15 U.S.C. § 1692 et seq.",
            "section": "§1692e",
            "summary": (
                "Prohibits false, deceptive, and misleading representations by debt collectors. "
                "Specifically prohibits: falsely implying government or attorney affiliation, "
                "misrepresenting the character, amount, or legal status of the debt, threatening "
                "legal action that cannot be taken or is not intended, using false business names, "
                "and failing to disclose that the communication is from a debt collector. "
                "The 'least sophisticated consumer' standard is applied — the prohibition covers "
                "statements that would mislead even the least sophisticated consumer."
            ),
            "effective_date": "1978-03-20",
            "category": "debt_collection",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-debt-collection-practices-act",
        },
        {
            "short_name": "FDCPA",
            "title": "Fair Debt Collection Practices Act",
            "citation": "15 U.S.C. § 1692 et seq.",
            "section": "§1692f",
            "summary": (
                "Prohibits unfair or unconscionable means to collect debts. "
                "Specifically bars: collecting amounts not expressly authorized by the agreement "
                "or permitted by law, depositing post-dated checks prematurely, causing charges "
                "(e.g., collect calls) to the consumer by concealing the purpose of communications, "
                "threatening to take or actually taking any non-judicial action to repossess property "
                "without a present right, communicating via postcard, and using any language or "
                "symbol on an envelope that indicates the communication is from a debt collector."
            ),
            "effective_date": "1978-03-20",
            "category": "debt_collection",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-debt-collection-practices-act",
        },
        {
            "short_name": "FDCPA",
            "title": "Fair Debt Collection Practices Act",
            "citation": "15 U.S.C. § 1692 et seq.",
            "section": "§1692g",
            "summary": (
                "Requires debt collectors to provide a written debt validation notice within 5 days "
                "of the initial communication. The notice must state: the amount of the debt, the "
                "name of the creditor, and a 30-day window during which the consumer may dispute "
                "the debt in writing. If the consumer disputes in writing within 30 days, the "
                "collector must cease collection until it obtains verification and mails it to the "
                "consumer. The collector must also provide the name and address of the original "
                "creditor if the consumer requests it within 30 days."
            ),
            "effective_date": "1978-03-20",
            "category": "debt_collection",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-debt-collection-practices-act",
        },
        {
            "short_name": "FDCPA",
            "title": "Fair Debt Collection Practices Act",
            "citation": "15 U.S.C. § 1692 et seq.",
            "section": "§1692k",
            "summary": (
                "Sets out civil liability for FDCPA violations. Any debt collector who fails to "
                "comply with any provision of the FDCPA is liable to the consumer for: "
                "(1) actual damages, (2) statutory damages up to $1,000 per action (regardless of "
                "whether actual damages are proven), and (3) attorney fees and costs. "
                "In class actions, statutory damages are capped at $500,000 or 1% of the debt "
                "collector's net worth. Courts may consider the frequency/persistence of "
                "noncompliance, nature of noncompliance, and extent to which it was intentional. "
                "Bona fide error defense available if violation was unintentional despite "
                "maintenance of reasonable procedures."
            ),
            "effective_date": "1978-03-20",
            "category": "debt_collection",
            "source_url": "https://www.ftc.gov/legal-library/browse/statutes/fair-debt-collection-practices-act",
        },
        # ── CROA ──────────────────────────────────────────────────────────────
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
        # ── ECOA ──────────────────────────────────────────────────────────────
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
        # ── TILA ──────────────────────────────────────────────────────────────
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
        # ── FACTA ─────────────────────────────────────────────────────────────
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
        # ── GLBA ──────────────────────────────────────────────────────────────
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
        # ── Regulation V ──────────────────────────────────────────────────────
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

    existing = set()
    for row in db.query(FederalLaw).with_entities(FederalLaw.citation, FederalLaw.section).all():
        existing.add((row.citation, row.section))

    added = 0
    for law_data in laws:
        key = (law_data["citation"], law_data["section"])
        if key not in existing:
            db.add(FederalLaw(**law_data))
            added += 1

    if added:
        db.commit()


def seed_agency_guidance(db):
    """Upsert CFPB/FTC agency guidance (keyed on agency+document_name)."""
    from app.models import AgencyGuidance

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
        {
            "agency": "FTC/CFPB",
            "document_name": "Red Flags Rule — Identity Theft Prevention Programs",
            "publication_date": "2013-05-01",
            "topic": "Identity Theft Prevention",
            "summary": (
                "Implements Section 315 of FACTA. Requires financial institutions and creditors to "
                "develop and implement written identity theft prevention programs designed to detect, "
                "prevent, and mitigate identity theft in connection with covered accounts. "
                "Programs must include policies for identifying relevant patterns, practices, and "
                "specific forms of activity ('red flags') that signal possible identity theft. "
                "Financial institutions must also respond appropriately when red flags are detected. "
                "The rule is codified at 16 C.F.R. § 681 (FTC) and 12 C.F.R. § 1022.40-42 (CFPB)."
            ),
            "source_url": "https://www.ftc.gov/business-guidance/privacy-security/red-flags-rule",
        },
        {
            "agency": "FTC",
            "document_name": "Disposal Rule — Proper Disposal of Consumer Report Information",
            "publication_date": "2005-06-01",
            "topic": "Data Security / Disposal of Consumer Reports",
            "summary": (
                "Implements Section 628 of FCRA (added by FACTA). Requires any person who maintains "
                "or possesses consumer report information for a business purpose to properly dispose "
                "of it in a manner that protects against unauthorized access and use. "
                "Covered entities must take reasonable measures to destroy such information — for "
                "example, burning, pulverizing, or shredding paper, and destroying electronic media. "
                "Violations may result in FTC enforcement action and civil liability under FCRA §§616-617. "
                "Codified at 16 C.F.R. § 682."
            ),
            "source_url": "https://www.ftc.gov/legal-library/browse/rules/disposal-rule",
        },
        {
            "agency": "CFPB",
            "document_name": "CFPB Circular 2022-03 — BNPL and Credit Reporting",
            "publication_date": "2022-09-15",
            "topic": "Buy Now Pay Later / Emerging Credit Products",
            "summary": (
                "CFPB guidance addressing whether consumer protection laws — including the FCRA — "
                "apply to buy-now-pay-later (BNPL) products. The CFPB found that many BNPL products "
                "are credit products subject to Regulation Z (TILA) and that BNPL lenders who report "
                "to credit bureaus must comply with FCRA §623 furnisher accuracy requirements. "
                "The guidance also raised concerns about lack of uniform credit reporting for BNPL "
                "products creating inaccurate or incomplete credit pictures for consumers. "
                "Relevant for analyzing whether non-traditional credit lines are accurately reported."
            ),
            "source_url": "https://www.consumerfinance.gov/compliance/circulars/",
        },
        {
            "agency": "CFPB",
            "document_name": "CFPB — Fair Debt Collection Practices Act Annual Report",
            "publication_date": "2023-03-01",
            "topic": "FDCPA Enforcement Trends",
            "summary": (
                "Annual CFPB report on FDCPA enforcement and supervision activities. "
                "Identifies top FDCPA complaint categories including false representations about "
                "debt amounts (§1692e), failure to provide debt validation notices (§1692g), "
                "harassment (§1692d), and improper third-party disclosures (§1692c). "
                "Data used to prioritize FDCPA supervisory examinations. Key resource for "
                "understanding current enforcement priorities and systemic debt collection issues."
            ),
            "source_url": "https://www.consumerfinance.gov/data-research/research-reports/",
        },
    ]

    existing = set()
    for row in db.query(AgencyGuidance).with_entities(AgencyGuidance.agency, AgencyGuidance.document_name).all():
        existing.add((row.agency, row.document_name))

    added = 0
    for g in guidance_records:
        key = (g["agency"], g["document_name"])
        if key not in existing:
            db.add(AgencyGuidance(**g))
            added += 1

    if added:
        db.commit()


def seed_case_law(db):
    """Upsert landmark FCRA/FDCPA cases (keyed on citation)."""
    from app.models import CaseLaw
    import json

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
            "case_name": "TransUnion LLC v. Ramirez",
            "citation": "594 U.S. 413 (2021)",
            "court": "U.S. Supreme Court",
            "jurisdiction": "Federal",
            "year": 2021,
            "topic": "FCRA Standing / Concrete Harm / Class Actions",
            "holding_summary": (
                "Only plaintiffs who suffer concrete harm from an FCRA violation have Article III "
                "standing to sue in federal court. The Court held that of 8,185 class members whose "
                "credit files contained false OFAC alerts, only the ~1,853 whose reports were "
                "actually disseminated to third parties suffered a concrete injury. Class members "
                "whose inaccurate files were never shared with third parties lacked standing. "
                "This decision significantly limits FCRA class action exposure for CRAs and furnishers."
            ),
            "legal_principle": (
                "Dissemination of inaccurate information to third parties is required for FCRA "
                "standing; a consumer whose inaccurate file exists internally but is never shared "
                "cannot sue in federal court. Narrows Spokeo and limits class action FCRA damages."
            ),
            "relevance_tags": json.dumps(["standing", "class action", "FCRA", "concrete harm", "Article III", "OFAC"]),
            "source_url": "https://www.supremecourt.gov/opinions/20pdf/20-297_20e2.pdf",
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
            "case_name": "Rotkiske v. Klemm",
            "citation": "589 U.S. 8 (2019)",
            "court": "U.S. Supreme Court",
            "jurisdiction": "Federal",
            "year": 2019,
            "topic": "FDCPA Statute of Limitations — Discovery Rule",
            "holding_summary": (
                "The FDCPA's 1-year statute of limitations (15 U.S.C. §1692k(d)) runs from the date "
                "of the violation, not from the date the consumer discovers the violation. "
                "The Court rejected the 'discovery rule' for FDCPA claims, holding that the plain "
                "text of the statute specifies that an action must be brought within one year 'from "
                "the date on which the violation occurs.' Only equitable tolling (fraud or active "
                "concealment) may extend the deadline, and only where the discovery rule exception "
                "within §1692k itself applies."
            ),
            "legal_principle": (
                "FDCPA claims must be filed within 1 year of the violation date, not the discovery "
                "date. The discovery rule does not apply to FDCPA §1692k(d) absent fraudulent "
                "concealment. Critical for evaluating timeliness of FDCPA claims."
            ),
            "relevance_tags": json.dumps(["FDCPA", "statute of limitations", "1692k", "discovery rule", "time-barred"]),
            "source_url": "https://www.supremecourt.gov/opinions/19pdf/18-328_i4dk.pdf",
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
        {
            "case_name": "Johnson v. MBNA America Bank, NA",
            "citation": "357 F.3d 426 (4th Cir. 2004)",
            "court": "U.S. Court of Appeals, Fourth Circuit",
            "jurisdiction": "4th Circuit",
            "year": 2004,
            "topic": "FCRA Furnisher Reasonable Investigation",
            "holding_summary": (
                "The Fourth Circuit held that FCRA §623(b) requires furnishers to conduct a "
                "reasonable investigation after receiving notice of a consumer's dispute from a CRA. "
                "The court rejected the argument that a furnisher satisfies its duty simply by "
                "checking its own records. Whether an investigation is 'reasonable' depends on "
                "what the furnisher knew at the time and what steps a reasonable furnisher would "
                "have taken given that knowledge. The case is foundational for furnisher liability."
            ),
            "legal_principle": (
                "Furnishers must conduct a reasonable investigation of disputes under FCRA §623(b). "
                "The reasonableness standard is fact-specific and requires more than an internal "
                "records check when the dispute raises legitimate factual questions."
            ),
            "relevance_tags": json.dumps(["furnisher", "FCRA §623", "reasonable investigation", "dispute"]),
            "source_url": "https://law.justia.com/cases/federal/appellate-courts/F3/357/426/594268/",
        },
        {
            "case_name": "Evon v. Law Offices of Sidney Mickell",
            "citation": "688 F.3d 1015 (9th Cir. 2012)",
            "court": "U.S. Court of Appeals, Ninth Circuit",
            "jurisdiction": "9th Circuit",
            "year": 2012,
            "topic": "FDCPA — False/Misleading Representations §1692e",
            "holding_summary": (
                "The Ninth Circuit applied the 'least sophisticated debtor' standard to assess "
                "whether a debt collection letter violated FDCPA §1692e. Under this standard, a "
                "collection communication is assessed from the perspective of the least "
                "sophisticated consumer — a consumer who may lack sophistication or legal knowledge "
                "but possesses a willingness to read and understand communications carefully. "
                "Statements that would be understood as false or misleading by such a consumer "
                "violate §1692e even if technically accurate."
            ),
            "legal_principle": (
                "FDCPA §1692e violations are assessed using the 'least sophisticated debtor' "
                "standard. Courts evaluate whether a communication would mislead the most "
                "vulnerable consumers, not a sophisticated or legally knowledgeable one."
            ),
            "relevance_tags": json.dumps(["FDCPA", "1692e", "least sophisticated debtor", "false representations", "collection letter"]),
            "source_url": "https://law.justia.com/cases/federal/appellate-courts/ca9/10-15888/10-15888-2012-07-13.html",
        },
    ]

    existing = set()
    for row in db.query(CaseLaw).with_entities(CaseLaw.citation).all():
        existing.add(row.citation)

    added = 0
    for c in cases:
        if c["citation"] not in existing:
            db.add(CaseLaw(**c))
            added += 1

    if added:
        db.commit()


def seed_state_laws(db):
    """Seed 10-state consumer protection laws, Bankruptcy Code, and SCRA entries."""
    from app.models import StateLaw

    STATE_LAWS = [
        # South Carolina
        {
            "state": "SC",
            "statute": "SC Consumer Protection Code",
            "citation": "S.C. Code Ann. § 37-5-108",
            "topic": "usury / consumer credit",
            "summary": (
                "South Carolina Consumer Protection Code § 37-5-108 restricts creditor remedies and "
                "prohibits unconscionable conduct. Creditors are barred from certain practices in the "
                "collection of consumer credit transactions, including harassment and deceptive acts. "
                "Violations can render portions of the credit agreement unenforceable."
            ),
            "effective_as_of": "1976-01-01",
        },
        {
            "state": "SC",
            "statute": "SC Debt Collection Licensing Requirements",
            "citation": "S.C. Code Ann. § 37-2-202",
            "topic": "debt_collection",
            "summary": (
                "South Carolina requires third-party debt collectors to obtain a license from the "
                "South Carolina Department of Consumer Affairs. Failure to hold a valid license bars "
                "collection activity in the state. The licensing scheme mirrors FDCPA consumer "
                "protections and adds state-specific requirements."
            ),
            "effective_as_of": "1976-01-01",
        },
        {
            "state": "SC",
            "statute": "SC Statute of Limitations",
            "citation": "S.C. Code Ann. § 15-3-530",
            "topic": "statute_of_limitations",
            "summary": (
                "South Carolina's general statute of limitations for written contracts and open "
                "accounts is 3 years. Consumer debt (credit cards, medical bills, personal loans) "
                "subject to written contract terms must be sued upon within 3 years of the date the "
                "cause of action accrued. The SOL on open accounts is also 3 years."
            ),
            "effective_as_of": "1988-01-01",
        },
        # New York
        {
            "state": "NY",
            "statute": "NY General Business Law Article 29-H",
            "citation": "N.Y. Gen. Bus. Law § 600 et seq.",
            "topic": "debt_collection",
            "summary": (
                "New York's Article 29-H prohibits abusive, harassing, and deceptive debt collection "
                "practices by creditors collecting their own debts — broader coverage than the federal "
                "FDCPA. Prohibits threats of arrest, public disclosure of debts, and communicating "
                "with third parties. Provides private right of action with actual and statutory damages."
            ),
            "effective_as_of": "1973-01-01",
        },
        {
            "state": "NY",
            "statute": "NY Statute of Limitations on Consumer Debt",
            "citation": "N.Y. C.P.L.R. § 214",
            "topic": "statute_of_limitations",
            "summary": (
                "New York's statute of limitations for consumer debt (credit cards, personal loans) "
                "is 3 years for most actions, effective for cases filed after April 2022 under "
                "the Statute of Limitations on Consumer Debts reform. Previously, the SOL was 6 years. "
                "Collectors must disclose when a debt is time-barred."
            ),
            "effective_as_of": "2022-04-07",
        },
        {
            "state": "NY",
            "statute": "NYC Debt Collection Licensing Act",
            "citation": "N.Y.C. Admin. Code § 20-490 et seq.",
            "topic": "debt_collection",
            "summary": (
                "New York City requires all third-party debt collectors operating within the five "
                "boroughs to hold a license issued by the NYC Department of Consumer and Worker "
                "Protection (DCWP). The license must be renewed annually. Unlicensed collection "
                "activity is a violation subject to fines and enforcement action."
            ),
            "effective_as_of": "1973-01-01",
        },
        # California
        {
            "state": "CA",
            "statute": "Rosenthal Fair Debt Collection Practices Act",
            "citation": "Cal. Civ. Code § 1788 et seq.",
            "topic": "debt_collection",
            "summary": (
                "California's Rosenthal Act extends FDCPA-style protections to original creditors, "
                "not just third-party collectors. Prohibits harassing, oppressive, and deceptive "
                "collection practices. Consumers may sue for actual damages, statutory damages up "
                "to $1,000, attorney fees, and costs. The California DFPI enforces the Act."
            ),
            "effective_as_of": "1977-01-01",
        },
        {
            "state": "CA",
            "statute": "CA Consumer Credit Reporting Agencies Act",
            "citation": "Cal. Civ. Code § 1785.1 et seq.",
            "topic": "credit_reporting",
            "summary": (
                "The CCRAA is California's state analog to the FCRA, providing enhanced consumer "
                "protections for California residents. Key additions: 7-year limit on all adverse "
                "information (without the bankruptcy exception), stricter furnisher accuracy duties, "
                "right to free reports twice per year, and a private right of action for willful or "
                "negligent violations."
            ),
            "effective_as_of": "1975-01-01",
        },
        {
            "state": "CA",
            "statute": "CA Statute of Limitations on Consumer Debt",
            "citation": "Cal. Civ. Proc. Code § 337, § 339",
            "topic": "statute_of_limitations",
            "summary": (
                "California's SOL for written contracts (including credit cards with written "
                "agreements) is 4 years from the date of default. Oral contracts carry a 2-year "
                "SOL. Under the 2013 Fair Debt Buying Practices Act, debt buyers must disclose the "
                "date of default and warn consumers when the debt may be time-barred."
            ),
            "effective_as_of": "1872-01-01",
        },
        # Florida
        {
            "state": "FL",
            "statute": "FL Consumer Collection Practices Act",
            "citation": "Fla. Stat. § 559.55 et seq.",
            "topic": "debt_collection",
            "summary": (
                "The FCCPA prohibits abusive, deceptive, and unfair practices by all persons "
                "collecting consumer debts, including original creditors. Prohibits communicating "
                "with the consumer at unusual times, using profane language, threatening criminal "
                "prosecution for civil debts, and disclosing the debt to third parties. "
                "Provides $1,000 statutory damages plus attorney fees per violation."
            ),
            "effective_as_of": "1993-01-01",
        },
        {
            "state": "FL",
            "statute": "FL Statute of Limitations",
            "citation": "Fla. Stat. § 95.11",
            "topic": "statute_of_limitations",
            "summary": (
                "Florida's SOL for written contracts (credit cards, installment loans) is 5 years. "
                "Open-account debt (e.g., revolving credit without a fixed written agreement) carries "
                "a 4-year SOL. The SOL begins to run from the date of the last payment or breach."
            ),
            "effective_as_of": "1974-01-01",
        },
        # Texas
        {
            "state": "TX",
            "statute": "TX Finance Code Chapter 392 — Debt Collection",
            "citation": "Tex. Fin. Code § 392.001 et seq.",
            "topic": "debt_collection",
            "summary": (
                "Texas Finance Code Chapter 392 prohibits debt collectors from using fraudulent, "
                "deceptive, misleading representations, threats of criminal prosecution, "
                "harassment, and unreasonable publication of debts. Applies to both original "
                "creditors and third-party collectors. Consumers may seek actual and punitive damages, "
                "attorney fees, and injunctive relief."
            ),
            "effective_as_of": "1997-09-01",
        },
        {
            "state": "TX",
            "statute": "TX Statute of Limitations",
            "citation": "Tex. Civ. Prac. & Rem. Code § 16.004",
            "topic": "statute_of_limitations",
            "summary": (
                "Texas applies a uniform 4-year statute of limitations to all consumer debt contracts, "
                "whether written or open-account. The SOL runs from the date of last activity or "
                "the date the debt became due and owing. Texas courts look to the date of last "
                "payment or charge as the accrual date."
            ),
            "effective_as_of": "1985-09-01",
        },
        # Georgia
        {
            "state": "GA",
            "statute": "GA Fair Business Practices Act",
            "citation": "O.C.G.A. § 10-1-390 et seq.",
            "topic": "consumer_protection",
            "summary": (
                "Georgia's FBPA prohibits unfair and deceptive trade practices in consumer "
                "transactions. The Act covers debt collection practices and credit-related "
                "transactions. Consumers may seek actual damages, civil penalties up to $5,000 per "
                "violation, and injunctive relief. The Georgia Attorney General has enforcement "
                "authority."
            ),
            "effective_as_of": "1975-01-01",
        },
        {
            "state": "GA",
            "statute": "GA Statute of Limitations",
            "citation": "O.C.G.A. § 9-3-24, § 9-3-25",
            "topic": "statute_of_limitations",
            "summary": (
                "Georgia's SOL for written contracts is 6 years. Open-account debt (e.g., credit "
                "cards treated as open accounts) carries a 4-year SOL. The distinction between a "
                "written contract (6 years) and an open account (4 years) can affect credit card "
                "debt depending on how the account agreement is characterized."
            ),
            "effective_as_of": "1895-01-01",
        },
        # North Carolina
        {
            "state": "NC",
            "statute": "NC Debt Collection Act",
            "citation": "N.C. Gen. Stat. § 75-50 et seq.",
            "topic": "debt_collection",
            "summary": (
                "North Carolina's Debt Collection Act prohibits abusive, deceptive, and unfair "
                "practices by all debt collectors, including original creditors. Specific "
                "prohibitions include threatening violence, using obscene language, disclosing "
                "the debt publicly, and making false representations about the debt. "
                "Violations are per se unfair trade practices under N.C.G.S. § 75-1.1."
            ),
            "effective_as_of": "1977-01-01",
        },
        {
            "state": "NC",
            "statute": "NC Statute of Limitations",
            "citation": "N.C. Gen. Stat. § 1-52",
            "topic": "statute_of_limitations",
            "summary": (
                "North Carolina's SOL for most consumer debt (credit cards, written contracts, "
                "open accounts) is 3 years. The SOL runs from the date of the last payment or the "
                "date the debt became due. North Carolina is a debtor-friendly state that strictly "
                "enforces its 3-year limitation period."
            ),
            "effective_as_of": "1868-01-01",
        },
        # Illinois
        {
            "state": "IL",
            "statute": "IL Collection Agency Act",
            "citation": "225 ILCS 425/1 et seq.",
            "topic": "debt_collection",
            "summary": (
                "Illinois requires all third-party debt collectors and collection agencies to be "
                "licensed by the Illinois Department of Financial and Professional Regulation (IDFPR). "
                "The Act prohibits unlicensed collection activity, harassment, deceptive practices, "
                "and misrepresentation of the debt. License revocation can result from FDCPA or "
                "IDFPR rule violations."
            ),
            "effective_as_of": "1993-01-01",
        },
        {
            "state": "IL",
            "statute": "IL Consumer Fraud and Deceptive Business Practices Act",
            "citation": "815 ILCS 505/1 et seq.",
            "topic": "consumer_protection",
            "summary": (
                "Illinois's consumer fraud statute broadly prohibits unfair or deceptive acts in "
                "trade or commerce. The Act applies to debt collection practices and credit "
                "reporting. Consumers may recover actual damages, civil penalties, punitive damages, "
                "and attorney fees. The Illinois Attorney General and private litigants both have "
                "enforcement rights."
            ),
            "effective_as_of": "1961-01-01",
        },
        {
            "state": "IL",
            "statute": "IL Statute of Limitations",
            "citation": "735 ILCS 5/13-205, 5/13-206",
            "topic": "statute_of_limitations",
            "summary": (
                "Illinois applies a 5-year SOL to written contracts and a 5-year SOL to open "
                "accounts. In 2019, Illinois courts clarified that credit card debt typically "
                "accrues when the cardholder defaults. The SOL on judgments is 7 years."
            ),
            "effective_as_of": "1980-01-01",
        },
        # Ohio
        {
            "state": "OH",
            "statute": "OH Consumer Sales Practices Act",
            "citation": "Ohio Rev. Code § 1345.01 et seq.",
            "topic": "consumer_protection",
            "summary": (
                "Ohio's CSPA prohibits unfair or deceptive acts or practices in consumer "
                "transactions. The Act has been applied to debt collection and credit reporting "
                "contexts by Ohio courts. Consumers may recover actual damages, treble damages "
                "(up to $200 per violation), rescission, and attorney fees. "
                "Class actions are available for CSPA violations."
            ),
            "effective_as_of": "1972-11-01",
        },
        {
            "state": "OH",
            "statute": "OH Statute of Limitations",
            "citation": "Ohio Rev. Code § 2305.07",
            "topic": "statute_of_limitations",
            "summary": (
                "Ohio's SOL for written contracts (including most consumer credit agreements) "
                "is 6 years from the date of default. Open-account debt also carries a 6-year "
                "limitation period. Ohio changed its rule on credit card debt from 15 years "
                "to 6 years in 2012."
            ),
            "effective_as_of": "2012-09-28",
        },
        # Virginia
        {
            "state": "VA",
            "statute": "VA Consumer Protection Act",
            "citation": "Va. Code Ann. § 59.1-196 et seq.",
            "topic": "consumer_protection",
            "summary": (
                "Virginia's Consumer Protection Act prohibits fraudulent, deceptive, and "
                "misleading conduct in consumer transactions, including debt collection. The Act "
                "provides consumers with a private right of action for actual damages, statutory "
                "damages up to $500, and attorney fees. Willful violations may result in triple "
                "damages up to $1,500."
            ),
            "effective_as_of": "1977-01-01",
        },
        {
            "state": "VA",
            "statute": "VA Statute of Limitations",
            "citation": "Va. Code Ann. § 8.01-246",
            "topic": "statute_of_limitations",
            "summary": (
                "Virginia's SOL for written contracts (including credit cards and consumer loans "
                "with written agreements) is 5 years from the date the cause of action accrues. "
                "Open-account or oral contract debt carries a 3-year SOL. Virginia courts apply "
                "the date of the last default as the accrual date for consumer debt."
            ),
            "effective_as_of": "1977-01-01",
        },
        # Bankruptcy Code
        {
            "state": "US",
            "statute": "Bankruptcy Code — Automatic Stay",
            "citation": "11 U.S.C. § 362",
            "topic": "bankruptcy",
            "summary": (
                "Upon the filing of a bankruptcy petition, § 362 imposes an automatic stay that "
                "immediately halts all collection efforts, lawsuits, wage garnishments, and "
                "foreclosure proceedings against the debtor. Creditors who violate the stay are "
                "subject to sanctions and damages. The stay provides the debtor breathing room to "
                "reorganize or liquidate assets under court supervision."
            ),
            "effective_as_of": "1979-10-01",
        },
        {
            "state": "US",
            "statute": "Bankruptcy Code — Nondischargeable Debts",
            "citation": "11 U.S.C. § 523",
            "topic": "bankruptcy",
            "summary": (
                "Section 523 enumerates debts that survive bankruptcy discharge, including: "
                "certain taxes, domestic support obligations (alimony and child support), student "
                "loans (absent undue hardship), debts from fraud, willful and malicious injury, "
                "fines and penalties owed to the government, and DUI-related obligations. "
                "Creditors must file adversary proceedings to establish nondischargeability."
            ),
            "effective_as_of": "1979-10-01",
        },
        {
            "state": "US",
            "statute": "Bankruptcy Code — Effect of Discharge",
            "citation": "11 U.S.C. § 524",
            "topic": "bankruptcy",
            "summary": (
                "Section 524 establishes the legal effect of the bankruptcy discharge order. "
                "The discharge eliminates personal liability for discharged debts and permanently "
                "enjoins creditors from pursuing collection of such debts against the debtor. "
                "Creditors who attempt to collect discharged debts may be held in contempt. "
                "Section 524(c) governs reaffirmation agreements that allow debtors to remain "
                "liable on otherwise dischargeable debts."
            ),
            "effective_as_of": "1979-10-01",
        },
        {
            "state": "US",
            "statute": "Bankruptcy Code — Chapter 7 Discharge",
            "citation": "11 U.S.C. § 727",
            "topic": "bankruptcy",
            "summary": (
                "Section 727 governs eligibility for Chapter 7 discharge. A court shall grant the "
                "debtor a discharge unless specific grounds for denial exist, including: prior "
                "discharge within 8 years, concealing or destroying records, failure to explain "
                "loss of assets, and failure to obey court orders. Section 727(b) broadly discharges "
                "all pre-petition debts except those enumerated in § 523."
            ),
            "effective_as_of": "1979-10-01",
        },
        # SCRA
        {
            "state": "US",
            "statute": "Servicemembers Civil Relief Act",
            "citation": "50 U.S.C. § 3901 et seq.",
            "topic": "servicemember_protection",
            "summary": (
                "The SCRA provides sweeping protections for active-duty military personnel "
                "in civil legal and financial matters. Key provisions: (1) interest rate cap of "
                "6% per year on pre-service obligations during active duty; (2) stay of civil "
                "proceedings, including collection lawsuits and eviction; (3) protection against "
                "default judgments without judicial determination of military status; (4) credit "
                "reporting protections preventing adverse reporting during SCRA-protected periods. "
                "The Department of Justice and affected servicemembers may sue for violations."
            ),
            "effective_as_of": "2003-12-19",
        },
    ]

    existing = set()
    for row in db.query(StateLaw).with_entities(StateLaw.state, StateLaw.citation).all():
        existing.add((row.state, row.citation))

    added = 0
    for law_data in STATE_LAWS:
        key = (law_data["state"], law_data["citation"])
        if key not in existing:
            law = StateLaw(**law_data)
            db.add(law)
            added += 1

    if added:
        db.commit()
