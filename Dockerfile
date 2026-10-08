FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/EricVilla0896/fastapi-practice"

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]