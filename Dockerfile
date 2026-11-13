# moodle-qc: run the question converter without a Python setup.
#
#   docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/questions" \
#     ghcr.io/peschmae/moodle-question-converter generate .
FROM python:3.13-slim

# git: extract refuses to overwrite question sources with uncommitted changes.
# The mounted collection belongs to another user, so git must trust every directory.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && git config --system --add safe.directory '*'

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . && rm -rf /app

# Runs as the host user (--user), who has no home directory in the image.
ENV HOME=/tmp
WORKDIR /questions
ENTRYPOINT ["moodle-qc"]
CMD ["--help"]
