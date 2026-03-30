import os
import json
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
    "1": {"name": "Chinook", "description": "Music store — artists, albums, tracks, sales", "path": "sqlite:///chinook.db"},
    "2": {"name": "Northwind", "description": "Trading company — orders, customers, products", "path": "sqlite:///northwind.db"},
    "3": {"name": "Custom", "description": "Load your own .db file", "path": None}
}

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
def create_chart(data_json: str) -> str:
    """
    IMPORTANT: You MUST use the actual query results as values. Never use example or estimated values.
    Creates a chart from SQL query results and saves it as a PNG file.
    Input must be JSON with keys: labels (list of strings), values (list of actual numbers from query results), title (str), xlabel (str), ylabel (str), chart_type (str: 'bar', 'line', 'pie').
    Example: {"labels": ["A", "B"], "values": [10.5, 20.3], "title": "My Chart", "xlabel": "X", "ylabel": "Y", "chart_type": "bar"}
    """
    try:
        data       = json.loads(data_json)
        labels     = data["labels"]
        values     = [float(v) for v in data["values"]]
        title      = data.get("title", "Chart")
        xlabel     = data.get("xlabel", "")
        ylabel     = data.get("ylabel", "Value")
        chart_type = data.get("chart_type", "bar")

        fig, ax = plt.subplots(figsize=(10, 6))

        if chart_type == "line":
            ax.plot(labels, values, color="steelblue", marker="o", linewidth=2)
            for i, val in enumerate(values):
                ax.text(i, val + max(values) * 0.01, f"{val:.2f}", ha="center", fontsize=10)
        elif chart_type == "pie":
            ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=140)
            ax.axis("equal")
        else:
            bars = ax.bar(labels, values, color="steelblue", edgecolor="white")
            for bar, val in zip(bars, values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(values) * 0.01,
                    f"{val:.2f}", ha="center", va="bottom", fontsize=10
                )

        if chart_type != "pie":
            ax.set_title(title, fontsize=14, fontweight="bold")
            ax.set_xlabel(xlabel, fontsize=11)
            ax.set_ylabel(ylabel, fontsize=11)
            plt.xticks(rotation=25, ha="right")
        else:
            ax.set_title(title, fontsize=14, fontweight="bold")

        plt.tight_layout()
        path = f"/app/charts/{title.replace(' ', '_')}.png"
        plt.savefig(path)
        plt.close()

        # Chart path'i global listeye ekle
        chart_paths.append(path)

        return f"Chart saved: {path}"

    except Exception as e:
        return f"Error creating chart: {str(e)}"

def generate_report(chat_history, db_name, chart_paths):
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M")
    path = f"/app/reports/report_{timestamp}.pdf"
    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("T", parent=styles["Title"], fontSize=22,
                                  textColor=colors.HexColor("#2C3E50"), spaceAfter=6)
    subtitle_style = ParagraphStyle("S", parent=styles["Normal"], fontSize=11,
                                     textColor=colors.HexColor("#7F8C8D"), spaceAfter=20)
    question_style = ParagraphStyle("Q", parent=styles["Normal"], fontSize=12,
                                     textColor=colors.HexColor("#2980B9"),
                                     fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6)
    answer_style = ParagraphStyle("A", parent=styles["Normal"], fontSize=11,
                                   textColor=colors.HexColor("#2C3E50"), spaceAfter=10, leading=16)
    elements = []
    elements.append(Paragraph("SQL Agent Report", title_style))
    elements.append(Paragraph(
        f"Database: {db_name} | Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#BDC3C7")))
    elements.append(Spacer(1, 0.5*cm))
    for i, (question, answer) in enumerate(chat_history, 1):
        elements.append(Paragraph(f"Q{i}: {question}", question_style))
        elements.append(Paragraph(answer.replace("\n", "<br/>"), answer_style))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#ECF0F1")))
    if chart_paths:
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("Charts", title_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#BDC3C7")))
        elements.append(Spacer(1, 0.3*cm))
        for chart_path in chart_paths:
            if os.path.exists(chart_path):
                elements.append(Image(chart_path, width=16*cm, height=9*cm))
                elements.append(Spacer(1, 0.5*cm))
    doc.build(elements)
    return path


db_path, db_name = select_database()
db = SQLDatabase.from_uri(db_path)

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

chat_history = []
chart_paths  = []  # Grafik yollarını takip et

agent = create_sql_agent(
    llm=llm,
    db=db,
    extra_tools=[create_chart],
    verbose=True,
    agent_type="openai-tools"
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
            llm=llm, db=db, extra_tools=[create_chart],
            verbose=True, agent_type="openai-tools"
        )
        chat_history = []
        chart_paths  = []
        print(f"Switched to: {db_name}\n")
        continue

    if not soru:
        continue

    if chat_history:
        full_input = "Previous conversation:\n"
        for q, a in chat_history:
            full_input += f"User: {q}\nAssistant: {a}\n"
        full_input += f"\nCurrent question: {soru}"
    else:
        full_input = soru

    response = agent.invoke(full_input)
    answer = response['output']
    chat_history.append((soru, answer))

    print(f"\nAnswer: {answer}\n")
    print("-" * 50)