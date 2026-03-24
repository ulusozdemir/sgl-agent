# SQL Agent with LangChain & Docker

Doğal dil sorularını SQL sorgularına çeviren bir AI agent.

## Kullanılan Teknolojiler
- LangChain
- Groq API (llama-3.3-70b-versatile)
- SQLite (Chinook Database)
- Docker

## Kurulum

1. Repoyu klonla
git clone https://github.com/ulusozdemir/sql_agent.git

2. .env dosyası oluştur
GROQ_API_KEY=gsk_xxxxxxxxxxxx

3. Chinook veritabanını indir
https://github.com/lerocha/chinook-database

4. Docker ile çalıştır
docker compose build
docker compose run -it sql-agent