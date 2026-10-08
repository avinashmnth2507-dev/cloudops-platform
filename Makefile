.PHONY: install test lint run docker-build docker-run
install:
	python3 -m pip install -r requirements.txt
test:
	pytest -q
lint:
	ruff check .
run:
	uvicorn app.main:app --reload
docker-build:
	docker build -t cloudops-platform:local .
docker-run:
	docker run --rm -p 8000:8000 cloudops-platform:local
