FROM nvcr.io/nvidia/pytorch:24.01-py3

WORKDIR /app

# Copia los requisitos
COPY requirements.txt .

# Instala TODO desde el archivo de requisitos.
# El pip dentro de este contenedor está optimizado para CUDA.
RUN pip install --no-cache-dir -r requirements.txt

# Copia el proyecto
COPY . .

# Establece el directorio de trabajo
WORKDIR /app/Revit-Agent/agent-revit-coder

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]