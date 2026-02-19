FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Generate the digest at build time
RUN python main.py

EXPOSE 8080

CMD ["python", "server.py"]
