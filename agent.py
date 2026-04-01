import os
import json
import re
import ast
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, HRFlowable
from reportlab.lib import colors

from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_groq import ChatGroq
from langchain.tools import tool


DATABASES = {
    "1": {
        "name": "Chinook",
        "description": "Music store — artists, albums, tracks, sales",
        "path": "sqlite:///chinook.db"
    },
    "2": {
        "name": "Northwind",
        "description": "Trading company — orders, customers, products",
        "path": "sqlite:///northwind.db"
    },
    "3": {
        "name": "Custom",
        "description": "Load your own .db file",
        "path": None
    }
}

# Global state
LAST_QUERY_RESULT = []
LAST_SQL_QUERY = ""
chart_paths = []
chat_history = []

# Ensure output folders exist
os.makedirs("/app/charts", exist_ok=True)
os.makedirs("/app/reports", exist_ok=True)

prefix = """You are a SQL expert and data visualization agent.

CHART WORKFLOW - ALWAYS FOLLOW THIS ORDER:
1. Run sql_db_list_tables
2. Run sql_db_schema to check exact column names
3. Run run_sql_query and get REAL results
4. If the user asks for a chart, call create_chart
5. NEVER use placeholder values like [100, 200] or [10, 20]
6. NEVER invent labels or values for charts
7. create_chart will automatically use the REAL latest SQL query result stored by the system
8. When calling create_chart, provide ONLY chart metadata:
   - chart_type
   - title
   - xlabel
   - ylabel

IMPORTANT:
- Do NOT send labels to create_chart
- Do NOT send values to create_chart
- The system will generate labels and values from the latest SQL query result
- If there is no valid SQL result, do not attempt to create a chart

SQLite rules:
- Use STRFTIME('%m', column) not EXTRACT()
- Table names with spaces must be wrapped in double quotes: "Order Details"
- NEVER rename or assume table names

After calling create_chart, structure your final answer using these tags:
<reasoning>your thought process</reasoning>
<sql>the query you ran</sql>
<answer>final answer to user</answer>
"""


def select_database():
    print("\n========================================")
    print("        SQL Agent - Database Select     ")
    print("========================================")
    for key, val in DATABASES.items():
        print(f"  {key}. {val['name']} — {val['description']}")
    print("========================================\n")

    while True:
        choice = input("Select database (1/2/3): ").strip()

        if choice not in DATABASES:
            print("Invalid choice.\n")
            continue

        if choice == "3":
            path = input("Enter your .db file path: ").strip()
            if not os.path.exists(path):
                print("File not found.\n")
                continue
            return f"sqlite:///{path}", "Custom"

        return DATABASES[choice]["path"], DATABASES[choice]["name"]


@tool
def create_chart(chart_json: str) -> str:
    """
    Create a chart ONLY from the latest real SQL result stored by Python.

    Input JSON format:
    {
        "chart_type": "bar|line|pie",
        "title": "str",
        "xlabel": "str",
        "ylabel": "str"
    }

    STRICT RULES:
    - NEVER provide labels or values
    - The chart will be created only from LAST_QUERY_RESULT
    - If there is no real SQL result, chart creation fails
    """
    global chart_paths, LAST_QUERY_RESULT

    try:
        if not LAST_QUERY_RESULT:
            return "Error creating chart: no SQL result available."

        spec = json.loads(chart_json)
        chart_type = spec.get("chart_type", "bar")
        title = spec.get("title", "Chart")
        xlabel = spec.get("xlabel", "")
        ylabel = spec.get("ylabel", "Value")

        rows = LAST_QUERY_RESULT

        if not isinstance(rows, list) or len(rows) == 0:
            return "Error creating chart: empty SQL result."

        if len(rows[0]) < 2:
            return "Error creating chart: SQL result must contain at least 2 columns."

        labels = [str(row[0]) for row in rows]
        values = [float(row[1]) for row in rows]

        fig, ax = plt.subplots(figsize=(10, 6))

        if chart_type == "line":
            ax.plot(labels, values, marker="o", linewidth=2)
            for i, val in enumerate(values):
                ax.text(i, val + max(values) * 0.01, f"{val:.2f}", ha="center", fontsize=10)

        elif chart_type == "pie":
            ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=140)
            ax.axis("equal")

        else:
            bars = ax.bar(labels, values)
            for bar, val in zip(bars, values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(values) * 0.01,
                    f"{val:.2f}",
                    ha="center",
                    va="bottom",
                    fontsize=10
                )

        ax.set_title(title, fontsize=14, fontweight="bold")

        if chart_type != "pie":
            ax.set_xlabel(xlabel, fontsize=11)
            ax.set_ylabel(ylabel, fontsize=11)
            plt.xticks(rotation=25, ha="right")

        plt.tight_layout()

        safe_title = "".join(
            c if c.isalnum() or c in (" ", "_", "-") else "_"
            for c in title
        ).strip()

        path = f"/app/charts/{safe_title.replace(' ', '_')}.png"
        plt.savefig(path)
        plt.close()

        chart_paths.append(path)
        return f"Chart saved: {path}"

    except Exception as e:
        return f"Error creating chart: {str(e)}"

@tool
def run_sql_query(query: str) -> str:
    """
    Execute SQL query and store the result for chart generation.
    ALWAYS use this tool to run queries.
    """
    global LAST_QUERY_RESULT, LAST_SQL_QUERY

    try:
        LAST_SQL_QUERY = query
        result = db.run(query)

        if isinstance(result, str):
            try:
                parsed = ast.literal_eval(result)
            except:
                parsed = []
        else:
            parsed = result

        if isinstance(parsed, list):
            LAST_QUERY_RESULT = parsed
        elif isinstance(parsed, tuple):
            LAST_QUERY_RESULT = list(parsed)
        else:
            LAST_QUERY_RESULT = []

        return str(result)

    except Exception as e:
        LAST_QUERY_RESULT = []
        return f"SQL Error: {str(e)}"

def generate_report(chat_history, db_name, chart_paths):
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M")
    path = f"/app/reports/report_{timestamp}.pdf"

    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "T",
        parent=styles["Title"],
        fontSize=22,
        textColor=colors.HexColor("#2C3E50"),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "S",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#7F8C8D"),
        spaceAfter=20
    )
    question_style = ParagraphStyle(
        "Q",
        parent=styles["Normal"],
        fontSize=12,
        textColor=colors.HexColor("#2980B9"),
        fontName="Helvetica-Bold",
        spaceBefore=14,
        spaceAfter=6
    )
    answer_style = ParagraphStyle(
        "A",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#2C3E50"),
        spaceAfter=10,
        leading=16
    )

    elements = []
    elements.append(Paragraph("SQL Agent Report", title_style))
    elements.append(
        Paragraph(
            f"Database: {db_name} | Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            subtitle_style
        )
    )
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#BDC3C7")))
    elements.append(Spacer(1, 0.5 * cm))

    for i, (question, answer) in enumerate(chat_history, 1):
        elements.append(Paragraph(f"Q{i}: {question}", question_style))
        elements.append(Paragraph(answer.replace("\n", "<br/>"), answer_style))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#ECF0F1")))

    if chart_paths:
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(Paragraph("Charts", title_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#BDC3C7")))
        elements.append(Spacer(1, 0.3 * cm))

        for chart_path in chart_paths:
            if os.path.exists(chart_path):
                elements.append(Image(chart_path, width=16 * cm, height=9 * cm))
                elements.append(Spacer(1, 0.5 * cm))

    doc.build(elements)
    return path


def extract_and_store_sql_result(answer: str, db):
    global LAST_QUERY_RESULT, LAST_SQL_QUERY

    sql_match = re.search(r"<sql>(.*?)</sql>", answer, re.DOTALL)

    if not sql_match:
        LAST_QUERY_RESULT = []
        LAST_SQL_QUERY = ""
        return

    LAST_SQL_QUERY = sql_match.group(1).strip()

    try:
        raw_result = db.run(LAST_SQL_QUERY)

        if isinstance(raw_result, str):
            try:
                parsed = ast.literal_eval(raw_result)
            except Exception:
                parsed = []
        else:
            parsed = raw_result

        if isinstance(parsed, list):
            LAST_QUERY_RESULT = parsed
        elif isinstance(parsed, tuple):
            LAST_QUERY_RESULT = list(parsed)
        else:
            LAST_QUERY_RESULT = []

    except Exception:
        LAST_QUERY_RESULT = []
        LAST_SQL_QUERY = ""


db_path, db_name = select_database()
db = SQLDatabase.from_uri(db_path)

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0
)

agent = create_sql_agent(
    llm=llm,
    db=db,
    extra_tools=[run_sql_query, create_chart],
    verbose=True,
    agent_type="openai-tools",
    prefix=prefix
)

print(f"\n SQL Agent ready! Connected to: {db_name}")
print("Commands: 'q' quit | 'switch' change database | 'report' export PDF\n")

while True:
    soru = input("Question: ").strip()

    if soru.lower() in ["q", "quit"]:
        print("Goodbye!")
        break

    if soru.lower() == "report":
        if not chat_history:
            print("No conversation yet!\n")
            continue

        path = generate_report(chat_history, db_name, chart_paths)
        print(f"\nPDF saved: {path}\n")
        continue

    if soru.lower() == "switch":
        db_path, db_name = select_database()
        db = SQLDatabase.from_uri(db_path)

        agent = create_sql_agent(
            llm=llm,
            db=db,
            extra_tools=[run_sql_query, create_chart],
            verbose=True,
            agent_type="openai-tools",
            prefix=prefix
        )

        chat_history.clear()
        chart_paths.clear()
        LAST_QUERY_RESULT = []
        LAST_SQL_QUERY = ""

        print(f"Switched to: {db_name}\n")
        continue

    if not soru:
        continue

    if chat_history:
        full_input = "Previous conversation:\n"
        for q, a in chat_history[-3:]:
            full_input += f"User: {q}\nAssistant: {a}\n"
        full_input += f"\nCurrent question: {soru}"
    else:
        full_input = soru

    response = agent.invoke(full_input)
    answer = response["output"]

    extract_and_store_sql_result(answer, db)

    chat_history.append((soru, answer))

    print(f"\nAnswer: {answer}\n")
    print("-" * 50)