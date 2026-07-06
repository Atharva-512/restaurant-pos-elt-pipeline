build:
	docker compose build

run:
	docker compose up

down:
	docker compose down

rebuild:
	docker compose down
	docker compose build --no-cache
	docker compose up

logs:
	docker compose logs -f

shell:
	docker compose run --rm restaurant-pos-pipeline /bin/bash

clean:
	docker system prune -f