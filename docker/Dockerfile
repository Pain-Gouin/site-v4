ARG PYTHON_VERSION=3.13
ARG APP_HOME=/app
# wether to include dev dependencies
ARG MINIMAL=1

# Stage 1: Python and tailwind build stage
FROM ghcr.io/astral-sh/uv:0.10-python${PYTHON_VERSION}-trixie AS builder

ARG APP_HOME
ARG NODE_MAJOR=24
ARG MINIMAL

# Set the working directory
WORKDIR ${APP_HOME}

# Set environment variables to optimize Python
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_NO_DEV=${MINIMAL} \
    MINIMAL=${MINIMAL}

# Requirements are installed here to ensure they will be cached.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Source the python env
ENV PATH="${APP_HOME}/.venv/bin:$PATH"

# Necessary for django-tailwind python package
RUN mkdir -p /etc/apt/keyrings \
  && curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - \
  && apt-get install nodejs -y \
  && rm -rf /var/lib/apt/lists/* /usr/share/doc /usr/share/man \
  && apt-get clean

# Copy application code
COPY . .

# Install and build tailwind
RUN python manage.py tailwind install --no-package-lock
RUN python manage.py tailwind build

# Remove development files that are not needed anymore to save space
RUN rm -rf theme/static_src

# Stage 2: Production stage
FROM python:${PYTHON_VERSION}-slim-trixie

ARG APP_HOME
ARG COMMIT_SHA \
    MINIMAL

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
  --disabled-password \
  --gecos "" \
  --home "/nonexistent" \
  --shell "/sbin/nologin" \
  --no-create-home \
  --uid "${UID}" \
  appuser && \
  mkdir ${APP_HOME} && \
  chown -R appuser ${APP_HOME}

# Set the working directory
WORKDIR ${APP_HOME}

# Necessary at runtime for mysqlclient python package
RUN apt-get update && apt-get install -y libmariadb3 \
  && rm -rf /var/lib/apt/lists/* /usr/share/doc /usr/share/man \
  && apt-get clean

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy application code
COPY --from=builder --chown=appuser:appuser ${APP_HOME}/ .

# Switch to non-root user
USER appuser

# Source the python env
ENV PATH="/app/.venv/bin:$PATH"

ENV GIT_COMMIT_SHA=$COMMIT_SHA \
    MINIMAL=$MINIMAL

# Generate static files
RUN python manage.py collectstatic --noinput

# Expose the application port
EXPOSE 8000

RUN ["chmod", "+x", "docker-entrypoint.sh"]
ENTRYPOINT ["./docker-entrypoint.sh"]

LABEL org.opencontainers.image.description="Minimal django container for the PainGouin website"
