import os
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_groq import ChatGroq
from langchain.tools import tool

def safe_str(text):
    if not isinstance(text, str):
        text = str(text)
    return text.encode("utf-8", "ignore").decode("utf-8")


db = SQLDatabase.from_uri("sqlite:///chinook.db")


llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0
)


@tool
def create_chart(data_json: str) -> str:
    """
    Creates a chart from SQL query results and saves it as a PNG file.
    Input must be JSON with keys: labels (list), values (list), title (str), xlabel (str), ylabel (str), chart_type (str: 'bar', 'line', 'pie').
    Example: {"labels": ["A", "B"], "values": [10, 20], "title": "My Chart", "xlabel": "X", "ylabel": "Y", "chart_type": "line"}
    """
    try:
        data = json.loads(data_json)
        labels     = data["labels"]
        values     = data["values"]
        title      = data.get("title", "Chart")
        xlabel     = data.get("xlabel", "")
        ylabel     = data.get("ylabel", "Value")
        chart_type = data.get("chart_type", "bar")  # varsayılan bar

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


agent = create_sql_agent(
    llm=llm,
    db=db,
    extra_tools=[create_chart],
    verbose=True,
    agent_type="openai-tools"
)


chat_history = []

print("\n SQL Agent with Memory ready!")
print("Type 'q' to quit.\n")

while True:
    soru = safe_str(input("Question: ").strip())

    if soru.lower() in ["q", "quit"]:
        print("Goodbye!")
        break

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