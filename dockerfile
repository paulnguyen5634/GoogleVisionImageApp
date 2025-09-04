# syntax=docker/dockerfile:1
FROM python:3.12-slim

# -- Build args let devcontainer set your host UID/GID so files aren't owned by root
ARG UID=1000
ARG GID=1000

# -- Basic env for clean, chatty Python and smaller images
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# -- Create a non-root user that matches host uid/gid (for clean file perms)
RUN groupadd -g ${GID} dev && \
    useradd -m -u ${UID} -g ${GID} dev

# -- Workdir inside the container (your repo will be bind-mounted here)
WORKDIR /app

# -- Install Python deps separately to leverage Docker layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt

# -- Use non-root by default
USER dev

# -- No forced entrypoint; you'll bind-mount code and run whatever you want
CMD ["bash"]