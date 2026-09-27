FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /opt/project
COPY requirements-monitoring.txt .
RUN pip install -r requirements-monitoring.txt
COPY monitoring/drift_monitor.py /opt/project/monitoring/drift_monitor.py
RUN mkdir -p /reports
CMD ["python", "monitoring/drift_monitor.py"]
