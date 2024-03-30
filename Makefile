# Makefile

# Commandes Docker Compose
start:
	docker-compose up --build -d
	@echo "Launched docker-compose"
	@sleep 10
	cd nifi/ && ./init-nifi.sh
	cd ../ && cd kafka-connect/ && ./init-kafka-connect.sh
	@echo "created kafka-connect connector"

down:
	docker compose down

build:
	docker compose build

kill:
	docker compose kill

restart:
	docker compose restart

logs:
	docker compose logs -f