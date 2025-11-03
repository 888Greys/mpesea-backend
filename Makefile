.PHONY: help build up down restart logs ps clean test

help:
	@echo "M-Pesa Tracker - Docker Commands"
	@echo ""
	@echo "make build     - Build Docker image"
	@echo "make up        - Start containers"
	@echo "make down      - Stop containers"
	@echo "make restart   - Restart containers"
	@echo "make logs      - View logs"
	@echo "make ps        - Show container status"
	@echo "make clean     - Remove containers and volumes"
	@echo "make test      - Test the API"
	@echo "make shell     - Open shell in container"

build:
	docker compose build

up:
	docker compose up -d
	@echo "Backend started at http://localhost:8000"

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

ps:
	docker compose ps

clean:
	docker compose down -v
	@echo "All containers and volumes removed"

test:
	@echo "Testing health endpoint..."
	@curl -s http://localhost:8000/health | jq
	@echo "\nTesting webhook endpoint..."
	@curl -s -X POST http://localhost:8000/webhook/sms \
		-H "Content-Type: application/json" \
		-d '{"sender":"MPESA","message":"RK12AB34CD confirmed. You have sent Ksh500.00 to TEST. Balance is Ksh1,000.00.","timestamp":1699000000000}' | jq

shell:
	docker compose exec mpesa-backend bash
