FROM bcgovimages/von-image:py36-1.16-1 AS base

# Install and configure poetry
USER root

ENV POETRY_VERSION=1.1.11
ENV POETRY_HOME=/opt/poetry
RUN curl -sSL https://install.python-poetry.org | python -

ENV PATH="/opt/poetry/bin:$PATH"
RUN poetry config virtualenvs.in-project true

# Setup project
RUN mkdir plugins && touch plugins/__init__.py
COPY pyproject.toml poetry.lock README.md ./
RUN poetry install --no-dev -E indy
USER $user

FROM bcgovimages/von-image:py36-1.16-1
COPY --from=base /home/indy/.venv /home/indy/.venv
ENV PATH="/home/indy/.venv/bin:$PATH"
EXPOSE 80

COPY docker/default.yml .
COPY plugins/ plugins/

ENTRYPOINT ["/bin/bash", "-c", "aca-py \"$@\"", "--"]
CMD ["start", "--arg-file", "default.yml"]