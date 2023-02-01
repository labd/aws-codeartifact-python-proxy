
install: check_venv
	pip install -r requirements.txt

check_venv:
	@test "${VIRTUAL_ENV}" || ( echo "Please activate your virtualenv"; exit 1; )
