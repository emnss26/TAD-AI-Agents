FROM nvcr.io/nvidia/pytorch:24.01-py3
WORKDIR /app

# 1. Instalar PyTorch estable para crear una base sólida
RUN pip install --no-cache-dir torch==2.3.1+cu121 torchvision==0.18.1+cu121 --index-url https://download.pytorch.org/whl/cu121

# 2. Instalar el resto de dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. ELIMINAR EL PAQUETE CONFLICTIVO
RUN pip uninstall -y transformer-engine

# 4. Copiar código y ejecutar
COPY . .
WORKDIR /app/Revit-Agent/agent-revit-coder
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]