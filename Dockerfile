FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/EricVilla0896/fastapi-practice"

WORKDIR /app

COPY requirements-prod.txt .

RUN pip install --no-cache-dir torch==2.14.1 \
--index-url https://download.pytorch.org/whl/cpu \
&& pip install --no-cache-dir -r requirements-prod.txt \
--extra-index-url https://download.pytorch.org/whl/cpu

COPY database.py database_docker.py main.py ./

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]