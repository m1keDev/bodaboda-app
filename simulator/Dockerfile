FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY driver_sim.py .

# -u flag = unbuffered output so logs appear immediately in docker logs
CMD ["python", "-u", "driver_sim.py"]