import os
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
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
            print("Invalid choice, please enter 1, 2 or 3.\n")
            continue

        if choice == "3":
            path = input("Enter your .db file path: ").strip()
            if not os.path.exists(path):
                print("File not found, please try again.\n")
                continue
            return f"sqlite:///{path}", "Custom"

        db_info = DATABASES[choice]
        return db_info["path"], db_info["name"]

@tool
def create_chart(data_json: str) -> str:
    """
    Creates a chart from SQL query results and saves it as a PNG file.
    Input must be JSON with keys: labels (list), values (list), title (str), xlabel (str), ylabel (str), chart_type (str: 'bar', 'line', 'pie').
    Example: {"labels": ["A", "B"], "values": [10, 20], "title": "My Chart", "xlabel": "X", "ylabel": "Y", "chart_type": "bar"}
    """
    try:
        data       = json.loads(data_json)
        labels     = data["labels"]
        values     = data["values"]
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

        return f"Chart saved: {path}"

    except Exception as e:
        return f"Error creating chart: {str(e)}"

db_path, db_name = select_database()
db = SQLDatabase.from_uri(db_path)

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0
)

agent = create_sql_agent(
    llm=llm,
    db=db,
    extra_tools=[create_chart],
    verbose=True,
    agent_type="openai-tools"
)

chat_history = []

print(f"\n SQL Agent ready! Connected to: {db_name}")
print("Type 'q' to quit, 'switch' to change database.\n")

while True:
    soru = input("Question: ").strip()

    if soru.lower() in ["q", "quit"]:
        print("Goodbye!")
        break

    if soru.lower() == "switch":
        db_path, db_name = select_database()
        db = SQLDatabase.from_uri(db_path)
        agent = create_sql_agent(
            llm=llm,
            db=db,
            extra_tools=[create_chart],
            verbose=True,
            agent_type="openai-tools"
        )
        chat_history = []
        print(f"Switched to: {db_name}\n")
        continue

    if not soru:
        print("Please enter a question.\n")
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