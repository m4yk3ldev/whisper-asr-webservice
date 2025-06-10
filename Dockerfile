FROM jrottenberg/ffmpeg:4.4-ubuntu2004 AS ffmpeg

FROM python:3.12-bookworm

ENV POETRY_VENV=/app/.venv

RUN python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install poetry==2.1.1

ENV PATH="${PATH}:${POETRY_VENV}/bin"

WORKDIR /app

COPY . /app
COPY --from=ffmpeg /ffmpeg /usr/local/bin/ffmpeg

COPY pyproject.toml ./

RUN poetry config virtualenvs.in-project true
RUN poetry install

EXPOSE 9000

ENTRYPOINT ["whisper-asr-webservice"]
