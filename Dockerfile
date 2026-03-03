FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Generate the digest at build time (non-fatal — pre-committed output files serve as fallback)
RUN python main.py || echo "Digest generation failed — serving pre-committed digest"

EXPOSE 8080

CMD ["python", "server.py"]
