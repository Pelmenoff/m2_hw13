# Dockerfile
FROM python:3.12

RUN pip install poetry

WORKDIR /code

COPY pyproject.toml poetry.lock* /code/
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

COPY . /code/

CMD ["uvicorn", "project.main:app", "--host", "0.0.0.0", "--port", "8000"]
