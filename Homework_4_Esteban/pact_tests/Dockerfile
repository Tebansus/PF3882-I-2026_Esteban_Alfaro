FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Generate the Pact contracts (consumer tests) and then verify them against the
# live Catalog and Ticketing services (provider verification).
CMD ["python", "run_pact_tests.py"]
