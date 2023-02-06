
install: check_venv requirements.txt
	pip install -r requirements.txt

requirements.txt: requirements.in
	pip-compile -r requirements.in

check_venv:
	@test "${VIRTUAL_ENV}" || ( echo "Please activate your virtualenv"; exit 1; )

build:
	docker build -t aws-codeartifact-python-proxy:latest .
