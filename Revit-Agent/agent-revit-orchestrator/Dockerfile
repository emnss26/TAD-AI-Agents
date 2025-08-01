FROM nvcr.io/nvidia/pytorch:24.01-py3
WORKDIR /app
RUN pip install --no-cache-dir torch==2.3.1+cu121 torchvision==0.18.1+cu121 torchaudio==2.3.1+cu121 --index-url https://download.pytorch.org/whl/cu121
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
WORKDIR /app/Revit-Agent/agent-revit-orchestrator
EXPOSE 5000
CMD ["python", "orchestrator.py"]