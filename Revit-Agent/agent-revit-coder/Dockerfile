FROM nvidia/cuda:12.1.1-base-ubuntu22.04

# Instala Miniconda
RUN apt-get update && apt-get install -y wget bzip2 ca-certificates curl git && \
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/conda.sh && \
    bash /tmp/conda.sh -b -p /opt/conda && rm /tmp/conda.sh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
ENV PATH=/opt/conda/bin:$PATH

WORKDIR /app

# --- ORDEN CORRECTO Y DEFINITIVO ---

# 1. Copia SÓLO los archivos de dependencias. Esto aprovecha la caché de Docker.
COPY environment-ai.yml .
COPY Revit-Agent/agent-revit-coder/requirements.txt .

# 2. Acepta TOS e instala Mamba
RUN conda config --set always_yes yes --set changeps1 false && \
    conda tos accept --override-channels --channel defaults && \
    conda install -n base mamba -c conda-forge

# 3. Crea el entorno base de Conda (SIN los pip requirements)
RUN mamba env create -f environment-ai.yml && conda clean -afy

# 4. Activa el entorno 'ai' para los siguientes comandos
SHELL ["conda", "run", "-n", "ai", "/bin/bash", "-lc"]

# 5. AHORA SÍ: Instala las dependencias de Pip. El archivo ya existe en /app.
RUN pip install --no-cache-dir -r requirements.txt

# 6. Finalmente, copia el código fuente de tu aplicación.
COPY Revit-Agent/agent-revit-coder/ .

# 7. Expone el puerto y arranca.
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]