FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    JUPYTER_CONFIG_DIR=/home/jovyan/.jupyter \
    PYTHONPATH=/workspace/src

WORKDIR /workspace

RUN apt-get update \
    && apt-get install --yes --no-install-recommends fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 jovyan \
    && useradd --uid 1000 --gid 1000 --create-home jovyan

COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install --requirement /tmp/requirements.txt

COPY --chown=jovyan:jovyan . /workspace

USER jovyan

EXPOSE 8888

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--ServerApp.token=", "--ServerApp.password="]
