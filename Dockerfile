FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /workspace

ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev

COPY app app
COPY control_plane control_plane
COPY run.py run_control_plane.py ./
COPY scripts scripts

CMD ["uv", "run", "python", "run.py"]
