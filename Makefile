.PHONY: up down nuke logs topics sim train evaluate test lint bench chaos chaos-redis chaos-kafka chaos-postgres obs

RATE ?= 50

up:            ## start infra + core services
	docker compose up -d --build

obs:           ## start Prometheus + Grafana
	docker compose --profile obs up -d

down:
	docker compose down

nuke:          ## stop and delete all data
	docker compose down -v

logs:
	docker compose logs -f $(s)

topics:
	docker compose exec -T redpanda sh < infra/redpanda/create-topics.sh

sim:
	RATE=$(RATE) docker compose --profile sim up -d gateway-sim

train:
	docker compose --profile jobs run --rm ml-platform train

evaluate:
	docker compose --profile jobs run --rm ml-platform evaluate

test:
	pytest -q

lint:
	ruff check . && ruff format --check .

bench:
	locust -f benchmarks/locustfile.py --headless -u 200 -r 50 -t 2m --host http://localhost:8000 --csv benchmarks/results/run

chaos: chaos-redis chaos-kafka chaos-postgres

chaos-redis:
	docker compose stop redis && sleep 30 && docker compose start redis

chaos-kafka:
	docker compose stop redpanda && sleep 30 && docker compose start redpanda

chaos-postgres:
	docker compose stop postgres && sleep 30 && docker compose start postgres
