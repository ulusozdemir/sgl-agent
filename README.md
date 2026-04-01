# SQL AI Agent with LangChain

Natural language → SQL → Visualization → PDF Reporting

An AI-powered data analyst agent that converts natural language questions into SQL queries, executes them on real databases, generates charts, and exports full analytical reports.

# Features
-Natural language to SQL (NL2SQL)
-Multi-database support (Chinook, Northwind, Custom SQLite)
-Automatic chart generation (bar, line, pie)
-Hallucination-free charts (uses real SQL results only)
-PDF report generation with charts and Q&A history
-Conversational memory (context-aware queries)
-Dockerized environment

## Installation

1. Clone the repo
git clone https://github.com/ulusozdemir/sql_agent.git

2. Create .env
GROQ_API_KEY=gsk_xxxxxxxxxxxx

3. Add database
Download sample DB:
Chinook
Northwind

4. Run with Docker
docker compose build
docker compose run -it sql-agent

## Example Questions

Show total sales by country as a bar chart
Show monthly sales trend as a line chart
Show top 5 customers by total spending
Show sales distribution by category as a pie chart
Show average order value per customer