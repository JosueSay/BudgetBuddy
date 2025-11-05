# Python 3.12.3 slim, con herramientas de build visibles
FROM python:3.12.3-slim

# no usar -qq: queremos logs visibles
RUN apt-get update && apt-get install -y --no-install-recommends \
  make dos2unix tree bash git ca-certificates && \
  rm -rf /var/lib/apt/lists/*

# workdir
WORKDIR /app

# instalar deps de Python (cache friendly)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# entorno por defecto
ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1

# shell por defecto
SHELL ["/bin/bash", "-lc"]

# comando por defecto: shell interactivo
CMD ["bash"]
