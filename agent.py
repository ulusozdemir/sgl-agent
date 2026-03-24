import os
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_groq import ChatGroq

db = SQLDatabase.from_uri("sqlite:///chinook.db")

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0
)

agent = create_sql_agent(
    llm=llm,
    db=db,
    verbose=True,
    agent_type="openai-tools"
)

print("\n🗄️  Chinook Veritabanı SQL Agent'ına Hoşgeldiniz!")
print("Çıkmak için 'q' veya 'quit' yazın.\n")

while True:
    soru = input("❓ Sorunuz: ").strip()
    
    if soru.lower() in ["q", "quit"]:
        print("Görüşmek üzere!")
        break
    
    if not soru:
        print("Lütfen bir soru girin.\n")
        continue
    
    response = agent.invoke(soru)
    print(f"\n✅ Cevap: {response['output']}\n")
    print("-" * 50)