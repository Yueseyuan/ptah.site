# Authorization to Test / Rules of Engagement

Copy this file per engagement (e.g. `engagements/<client>/authorization.md`),
fill it in, and get it **signed by someone with legal authority over the
target systems** before any tool in this repo touches them. Verbal or email
"go ahead" is not sufficient — get a signature.

This document is the only thing standing between "authorized penetration
test" and a federal computer-crime charge. Do not run engagements without it.

## 1. Parties

- **Client (authorizing party):** ______________________
- **Signatory name & title:** ______________________ (must have authority to authorize testing of the systems below)
- **BlackOps engagement lead:** ______________________
- **Engagement dates:** from ______ to ______ (fixed window — testing outside this window is unauthorized)

## 2. Scope — in scope

List every domain, IP range, cloud account, AD forest, or phone number
explicitly authorized for testing. Nothing outside this list is in scope,
even if discovered incidentally during the engagement (see §4).

- Domains/subdomains: ______________________
- IP ranges/CIDRs: ______________________
- Cloud accounts (account IDs, not just names): ______________________
- AD domain(s)/forest(s): ______________________
- Phone numbers / identities for social-engineering scope: ______________________

## 3. Explicitly out of scope

- Third-party/vendor systems (SaaS, hosting, CDN) unless separately authorized by that vendor
- Production data destruction, ransomware simulation without prior written sign-off, physical intrusion unless separately scoped
- Any system not listed in §2, even if it appears to belong to the client

## 4. Handling out-of-scope discoveries

If testing incidentally reveals access to something outside scope (e.g. a
misconfigured third-party bucket, a subdomain not on the list), **stop, do not
exploit further, and report it to the engagement lead and client within 24
hours.** Do not treat "we found it" as "we're authorized to use it."

## 5. Tools authorized for this engagement

Check only what's approved for this specific engagement — not everything in
the toolkit is appropriate for every job.

- [ ] Shodan / passive OSINT (Maltego, SpiderFoot, Sherlock, PhoneInfoga, Recon-ng)
- [ ] Active recon (BBOT, subdomain brute-forcing)
- [ ] Cloud audit (CloudFox)
- [ ] Vulnerability scanning (Nuclei)
- [ ] Active Directory attack-path mapping (BloodHound) — requires domain credentials, list which account(s): ______________________
- [ ] Web app testing (Caido)
- [ ] Phishing/2FA-relay simulation (Evilginx3) — requires: exact phishlet domains: ______________________, exact target user list or clearly defined population: ______________________, and confirmation this doesn't violate the email provider's ToS in a way the client hasn't accepted

## 6. Emergency contact

- **Client emergency contact (available during testing window):** ______________________, phone: ______________________
- **If testing causes a service disruption:** stop immediately, notify the emergency contact, and document the timeline.

## 7. Data handling

- All recon output and findings are stored under `engagements/<client>/` locally, never committed to a shared/public repo.
- Findings and any captured credentials/sessions/PII are deleted or returned to the client per the retention terms agreed in the master services agreement, no later than: ______________________
- Final report delivered to: ______________________

## 8. Signatures

Client signatory: ______________________ Date: ______________

BlackOps engagement lead: ______________________ Date: ______________
