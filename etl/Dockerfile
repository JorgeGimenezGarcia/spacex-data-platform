FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY extract_spacex.py .
ENTRYPOINT ["python", "extract_spacex.py"]