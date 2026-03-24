FROM python:3.11-slim


WORKDIR /app


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


RUN apt-get update && apt-get install -y curl && \
    curl -L https://github.com/lerocha/chinook-database/raw/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite \
    -o chinook.db


COPY agent.py .


CMD ["python", "agent.py"]