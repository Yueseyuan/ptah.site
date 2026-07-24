# BlackOps — Internal Assessment Toolkit

Internal recon/vulnerability-assessment toolkit for BlackOps engagements. This
is **not** a customer-facing product — it's the infrastructure the operations
team runs against **authorized targets only**, under a signed scope of work.

Read [`AUTHORIZATION_TEMPLATE.md`](./AUTHORIZATION_TEMPLATE.md) before running
anything here against a client asset. Running any of these tools against a
system you don't have written authorization to test is a federal crime (CFAA)
and equivalent state/international law, regardless of intent.

## What's in the box

| Tool | Purpose | Install method |
|---|---|---|
| [Shodan CLI](https://cli.shodan.io/) | Internet-wide device/exposure search | pip, needs `SHODAN_API_KEY` |
| [SpiderFoot](https://github.com/smicallef/spiderfoot) | Automated OSINT aggregation (200+ modules) | official Docker image, own compose service, web UI |
| [Sherlock](https://github.com/sherlock-project/sherlock) | Username enumeration across 400+ sites | pip |
| [PhoneInfoga](https://github.com/sundowndev/phoneinfoga) | Phone number OSINT | Go binary |
| [Recon-ng](https://github.com/lanmaster53/recon-ng) | Modular recon framework | source (no PyPI package), built into toolkit image |
| [BBOT](https://github.com/blacklanternsecurity/bbot) | Recursive subdomain/asset discovery | pip |
| [CloudFox](https://github.com/BishopFox/cloudfox) | AWS/Azure/GCP privilege-escalation path mapping | Go binary |
| [Nuclei](https://github.com/projectdiscovery/nuclei) | Template-based vulnerability scanning (9000+ templates) | Go binary |
| [BloodHound CE](https://github.com/SpecterOps/BloodHound) | Active Directory attack-path graphing | Docker (official images) |
| [CyberChef](https://github.com/gchq/CyberChef) | Data decode/decrypt/transform workbench | Self-hosted static build |
| [Caido](https://caido.io/) | Web app proxy/intercept testing | Desktop app — manual install, not dockerized here |
| [Maltego](https://www.maltego.com/) | Link-analysis/entity graphing | Proprietary — manual license + install, not dockerized here |
| Evilginx3 | Phishing/2FA-bypass simulation | **Opt-in only**, see [Evilginx3 policy](#evilginx3-policy) below |

Caido and Maltego are commercial products with their own licensing and
installers — this toolkit doesn't (and can't) redistribute them. Everything
else builds from source/package index into the `toolkit` container.

## Setup

```bash
cd blackops
cp .env.example .env
# fill in SHODAN_API_KEY and a strong BLOODHOUND_NEO4J_PASSWORD
docker compose build
docker compose up -d neo4j bloodhound bloodhound-db spiderfoot cyberchef
docker compose run --rm toolkit bash    # drops you into the CLI toolkit container
```

`nuclei -update-templates` runs automatically on container start (entrypoint)
so template coverage stays current.

## Common workflows

Run these from inside the `toolkit` container (or via `docker compose run --rm toolkit <script>`).
Every script takes a target and writes timestamped output under `/engagements/<target>/`,
which is bind-mounted to `./engagements` on the host — keep that directory out
of version control (it's already gitignored) since it will contain live client
recon data.

```bash
scripts/shodan-search.sh "org:\"Acme Corp\""
scripts/recon.sh acme.com              # BBOT: passive+active subdomain/asset sweep
scripts/vuln-scan.sh targets.txt       # Nuclei: template-based scan over a host list
scripts/username-search.sh jdoe123     # Sherlock: cross-site username enumeration
scripts/phone-lookup.sh +18645551234   # PhoneInfoga
scripts/cloud-audit.sh                 # CloudFox: reads AWS creds from environment/profile
```

SpiderFoot and Recon-ng are interactive/web-driven tools — start them directly:

```bash
docker compose up -d spiderfoot   # web UI on http://localhost:5001
docker compose run --rm toolkit recon-ng
```

BloodHound CE's web UI is at `http://localhost:8080` once `docker compose up -d bloodhound` is running.
CyberChef is a static app at `http://localhost:8000`.

## Evilginx3 policy

Evilginx3 is a real phishing/2FA-relay framework. It is **not** built into the
default toolkit image and there is no wrapper script for it. It exists in
this repo only as a documented, opt-in build path for two specific uses:

1. Authorized phishing-simulation engagements with signed client authorization
   naming Evilginx3 and the exact domains/phishlets in scope.
2. Internal training/lab use against infrastructure you own, isolated from
   production networks.

To build it, see `docker/Dockerfile.evilginx3` — it is not included in
`docker-compose.yml` by default and must be built and run explicitly:

```bash
docker build -f docker/Dockerfile.evilginx3 -t blackops/evilginx3 .
```

Do not automate this against arbitrary targets. Do not add a script that
takes a target argument and runs it — that crosses from "tool a security firm
owns" into "phishing infrastructure," and this repo won't carry that.

## Secrets and output hygiene

- `.env` (API keys, DB passwords) is gitignored — never commit it.
- `engagements/` (scan output, recon data) is gitignored — this directory will
  contain live client data and must never be pushed to a shared repo.
- Rotate `SHODAN_API_KEY` and `BLOODHOUND_NEO4J_PASSWORD` if this repo or the
  `.env` file is ever exposed.
