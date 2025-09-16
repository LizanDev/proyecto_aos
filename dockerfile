# Imagen base (Python 3.10 o 3.11 suelen ir bien con Reflex)
FROM python:3.10-slim

# Crear y entrar al directorio de la app
WORKDIR /app

# Copiar requirements primero (mejor cacheo)
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Railway expone la var $PORT
ENV PORT=8000

# Comando de inicio
CMD ["reflex", "run", "--env", "prod", "--host", "0.0.0.0", "--port", "8000"]