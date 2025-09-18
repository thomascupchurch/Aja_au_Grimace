# Minimal image for the read-only web viewer
FROM python:3.11-slim

# Prevents Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
	PIP_NO_CACHE_DIR=1 \
	WEB_SQLITE_RO=1

WORKDIR /app

# Install web-only requirements
COPY web/requirements-web.txt /app/
RUN pip install --no-cache-dir -r requirements-web.txt

# Copy the web app
COPY web /app

# Expose the HTTP port
EXPOSE 8000

# Start gunicorn; app module is app.py with object `app`
CMD ["gunicorn","-w","2","-b","0.0.0.0:8000","app:app"]
# Minimal container for the read-only web viewer
FROM python:3.11-slim
WORKDIR /app
COPY requirements-web.txt /app/
RUN pip install --no-cache-dir -r requirements-web.txt
COPY . /app
# Read-only suggested for shared SMB/OneDrive paths
ENV WEB_SQLITE_RO=1
EXPOSE 8000
CMD ["gunicorn","-w","2","-b","0.0.0.0:8000","app:app"]
