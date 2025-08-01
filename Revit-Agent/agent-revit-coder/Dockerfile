FROM nvcr.io/nvidia/pytorch:24.01-py3

# Establecemos el directorio de trabajo raíz
WORKDIR /app

# Copia los requisitos e instálalos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia TODO el proyecto al contenedor
COPY . .

# *** CAMBIO CLAVE ***
# Nos movemos al directorio específico del agente
WORKDIR /app/Revit-Agent/agent-revit-coder

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]