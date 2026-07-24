.PHONY: build up down shell new-engagement recon vuln-scan username-search phone-lookup cloud-audit shodan-search

build:
	docker compose build

up:
	docker compose up -d neo4j bloodhound bloodhound-db spiderfoot cyberchef

down:
	docker compose down

shell:
	docker compose run --rm toolkit bash

new-engagement:
	docker compose run --rm toolkit scripts/new-engagement.sh "$(CLIENT)"

recon:
	docker compose run --rm toolkit scripts/recon.sh $(TARGET)

vuln-scan:
	docker compose run --rm toolkit scripts/vuln-scan.sh $(TARGET)

username-search:
	docker compose run --rm toolkit scripts/username-search.sh $(USERNAME)

phone-lookup:
	docker compose run --rm toolkit scripts/phone-lookup.sh $(NUMBER)

cloud-audit:
	docker compose run --rm toolkit scripts/cloud-audit.sh $(PROFILE)

shodan-search:
	docker compose run --rm toolkit scripts/shodan-search.sh "$(QUERY)"
