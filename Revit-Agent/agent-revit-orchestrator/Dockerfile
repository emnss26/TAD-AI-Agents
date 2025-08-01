FROM nvcr.io/nvidia/pytorch:24.01-py3

WORKDIR /app

COPY requirements.txt .

# 1. Instala las dependencias TERCERAS PRIMERO
RUN pip install --no-cache-dir -r requirements.txt

# 2. AHORA, instala PyTorch ESTABLE.
RUN pip install --no-cache-dir torch==2.3.1+cu121 torchvision==0.18.1+cu121 --index-url https://download.pytorch.org/whl/cu121

COPY . .

WORKDIR /app/Revit-Agent/agent-revit-orchestrator

EXPOSE 5000
CMD ["python", "orchestrator.py"]