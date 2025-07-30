import torch
print(torch.cuda.is_available())          # debería imprimir True
print(torch.cuda.get_device_name(0))      # debería mostrar "NVIDIA Quadro P3000"