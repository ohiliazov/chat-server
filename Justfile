help:
    just --list

install:
    poetry install --sync --no-interaction --no-root
    poetry run pre-commit install

format:
    poetry run pre-commit run --all

runserver:
    poetry run uvicorn chat_server.server:app --reload
