FROM nvidia/cuda:12.1.1-base-ubuntu22.04

# Instala Miniconda y utilidades
RUN apt-get update && apt-get install -y wget bzip2 ca-certificates curl git && \
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/conda.sh && \
    bash /tmp/conda.sh -b -p /opt/conda && rm /tmp/conda.sh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
ENV PATH=/opt/conda/bin:$PATH

WORKDIR /app

# ---- LA CORRECCIÓN CLAVE ----
# 1. COPIA el archivo de entorno a la imagen. Lo ponemos en /app para mantener todo ordenado.
# Como el contexto es '.', la ruta de origen es relativa a la raíz del proyecto.
COPY environment-ai.yml /app/environment-ai.yml

# 2. Acepta TOS e instala Mamba
RUN conda config --set always_yes yes --set changeps1 false && \
    conda tos accept --override-channels --channel defaults && \
    conda install -n base mamba -c conda-forge

# 3. Crea el entorno ai CON MAMBA usando la ruta CORRECTA
# El archivo ahora existe en /app/environment-ai.yml
RUN mamba env create -f /app/environment-ai.yml && conda clean -afy

# 4. Activa el entorno 'ai' para todos los comandos subsiguientes
SHELL ["conda", "run", "-n", "ai", "/bin/bash", "-lc"]

# 5. Copia el código específico del ORQUESTADOR y sus dependencias
COPY Revit-Agent/agent-revit-orchestrator/ /app
RUN pip install --no-cache-dir -r requirements.txt

# 6. Expone el puerto y define el comando de inicio
EXPOSE 5000
CMD ["python", "orchestrator.py"]