# Use lightweight python:3.13-slim as the base image
FROM python:3.13-slim

# Copy the uv executable from the official Astral uv image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory inside the container
WORKDIR /app

# Enable bytecode compilation for faster import times
ENV UV_COMPILE_BYTECODE=1

# Place the virtual environment outside of the source tree to prevent volume mounts from overwriting it
ENV UV_PROJECT_ENVIRONMENT="/opt/venv"
ENV PATH="/opt/venv/bin:$PATH"

# Copy configuration files first to leverage Docker's build cache
COPY pyproject.toml uv.lock ./

# Install project dependencies cleanly without installing the project package itself
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application files into the container
COPY . .

# Expose the API port
EXPOSE 8000

# Start the FastAPI application via uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]