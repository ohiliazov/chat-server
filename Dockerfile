FROM python:3.11.7-bookworm as builder
LABEL authors="ohiliazov"
ENV PATH="$PATH:/root/.local/bin"

RUN apt-get update -y && \
    apt-get install -y build-essential curl
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    poetry config virtualenvs.create false

WORKDIR /app
COPY poetry.lock pyproject.toml ./
RUN poetry install

FROM python:3.11.7-bookworm

EXPOSE 8000

COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

COPY chat_server ./chat_server

ENTRYPOINT ["uvicorn", "chat_server:app", "--host", "0.0.0.0", "--port", "8000"]
