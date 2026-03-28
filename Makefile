.PHONY: dev-up prod-up down test lint docker-build

dev-up:
	docker compose up --build

prod-up:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

down:
	docker compose down

test:
	cd orchestrator && pip install -q -r requirements.txt -r requirements-dev.txt && pytest -q

lint:
	cd frontend && npm run lint
	cd gateway && npm run build

docker-build:
	docker build -t rentai-orchestrator:local ./orchestrator
	docker build -t rentai-gateway:local ./gateway
