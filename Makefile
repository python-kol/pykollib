test:
	python -m unittest pykollib/test/**/test_*.py

install:
	pre-commit install
	pip install -r requirements.txt