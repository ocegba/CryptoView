# Makefile

# Commandes Docker Compose
up:
    docker-compose up -d

down:
    docker-compose down

build:
    docker-compose build

kill:
    docker-compose kill

restart:
    docker-compose restart

logs:
    docker-compose logs -f