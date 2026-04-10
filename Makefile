.PHONY: install discover test

install:
	poetry lock
	poetry install

discover:
	./bin/garmin-bridge scan

test:
	poetry run pytest -v
