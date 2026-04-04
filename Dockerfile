FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /workspace

ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev

COPY app app
COPY control_plane control_plane
COPY data data
COPY run.py run_control_plane.py ./
COPY scripts scripts

CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "60", "run:app"]
