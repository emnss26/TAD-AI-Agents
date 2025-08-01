FROM nvcr.io/nvidia/pytorch:24.01-py3

WORKDIR /app

# 1. Copia solo los requisitos
COPY requirements.txt .

# 2. Instala las dependencias TERCERAS PRIMERO
RUN pip install --no-cache-dir -r requirements.txt

# 3. AHORA, instala PyTorch ESTABLE.
#    Al instalarlo al final, SOBREESCRIBE cualquier versión incompatible
#    que las otras librerías hayan podido instalar.
RUN pip install --no-cache-dir torch==2.3.1+cu121 torchvision==0.18.1+cu121 --index-url https://download.pytorch.org/whl/cu121

# 4. Copia el resto del código
COPY . .

# 5. Establece el directorio de trabajo final
WORKDIR /app/Revit-Agent/agent-revit-coder

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]