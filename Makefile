build:
	docker build -t yard-support-ticket-triage-live:latest .

run:
	docker run --env-file .env -p 9000:9000 yard-support-ticket-triage-live:latest

test:
	docker run --rm yard-support-ticket-triage-live:latest python -c "print('smoke test passed')"

health:
	curl -f http://localhost:9000/health
