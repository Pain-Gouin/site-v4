# Stage 1: Python build stage
FROM python:3.12-bullseye AS builder_python

# Create the app directory
RUN mkdir /app

# Set the working directory
WORKDIR /app

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Upgrade pip and install dependencies
RUN pip install --upgrade pip 

# Copy the requirements file first (better caching)
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Tailwind build stage
FROM python:3.12-slim-bullseye AS builder_tailwind

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
  --disabled-password \
  --gecos "" \
  --home "/home/appuser" \
  --shell "/sbin/nologin" \
  --uid "${UID}" \
  appuser && \
  mkdir /app && \
  chown -R appuser /app

# Set the working directory
WORKDIR /app

# Necessary for django-tailwind python package, as well as for mySQL package
RUN apt-get update && apt-get install -y libmariadb3 curl \
  && mkdir -p /etc/apt/keyrings \
  && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
  && apt-get install nodejs -y \
  && rm -rf /var/lib/apt/lists/* /usr/share/doc /usr/share/man \
  && apt-get clean

# Copy application code
COPY --chown=appuser:appuser . .

# Copy the Python dependencies from the python builder stage
COPY --from=builder_python /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder_python /usr/local/bin/ /usr/local/bin/

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

# Set the correct settings file
RUN mv paingouin/settings.docker.py paingouin/settings.py

# Install and build tailwind
RUN python manage.py tailwind install --no-package-lock --no-input
RUN python manage.py tailwind build --no-input;

# Remove development files that are not needed anymore to save space
RUN rm -rf theme/static_src

# Stage 3: Production stage
FROM python:3.12-slim-bullseye

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
  mkdir /app && \
  chown -R appuser /app

# Set the working directory
WORKDIR /app

# Necessary at runtime for mysqlclient python package, and django-tailwind python package
RUN apt-get update && apt-get install -y libmariadb3 \
  && rm -rf /var/lib/apt/lists/* /usr/share/doc /usr/share/man \
  && apt-get clean

# Copy the Python dependencies from the python builder stage
COPY --from=builder_python /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder_python /usr/local/bin/ /usr/local/bin/

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy application code
COPY --from=builder_tailwind --chown=appuser:appuser /app/ .

# Switch to non-root user
USER appuser

# Generate static files
RUN python manage.py collectstatic --noinput

# Expose the application port
EXPOSE 8000

RUN ["chmod", "+x", "docker-entrypoint.sh"]
ENTRYPOINT ["./docker-entrypoint.sh"]
