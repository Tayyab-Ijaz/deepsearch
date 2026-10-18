FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
# Configure Firebase service-account credentials at runtime; Firestore is the persistent store.
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
# Put an HTTPS proxy (your host's load balancer, Caddy or nginx) in front of this.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
