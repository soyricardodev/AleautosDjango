# Usa una imagen base con Node.js
FROM node:20.5.1-slim

ENV DEBUG "True"
# Instala dependencias del sistema necesarias para compilar Python
RUN apt-get update && \
    apt-get install -y --no-install-recommends supervisor cron \
        build-essential \
        libssl-dev \
        zlib1g-dev \
        libbz2-dev \
        liblzma-dev \
        wget \
        && rm -rf /var/lib/apt/lists/*

WORKDIR /app/proyectoBallena # Asegúrate de que este sea el path correcto
COPY proyectoBallena/package*.json ./ 
RUN npm install
# Descarga y extrae Python 3.11.2
WORKDIR /tmp
RUN wget --no-check-certificate https://www.python.org/ftp/python/3.11.2/Python-3.11.2.tgz
RUN tar xzf Python-3.11.2.tgz

# Compila e instala Python
WORKDIR /tmp/Python-3.11.2
RUN ./configure --enable-optimizations
RUN make -j$(nproc)
RUN make altinstall

# Limpia los archivos temporales
WORKDIR /
RUN rm -rf /tmp/*

# Establece el directorio de trabajo
WORKDIR /app

# Copia el archivo requirements.txt (SI EXISTE)
COPY requirements.txt .

# Instala las dependencias de Python si existe el archivo requirements.txt
RUN if [ -f "requirements.txt" ]; then pip3.11 install -r requirements.txt; fi

# Laravel entrypoint script
COPY ./docker/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Copy Supervisor configuration
COPY ./docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copia los archivos de tu aplicación
COPY . /app

ENV DJANGO_SETTINGS_MODULE=proyectoBallena.settings
RUN python3.11 manage.py collectstatic --noinput

EXPOSE 8000

ENTRYPOINT [ "docker-entrypoint.sh" ]