from agent.agent import agent

def main():
    print("Hello from deploybot!")
    response = agent.invoke({"messages": [("human", "Does Immich have any recent CVEs?")]})
    print(response["messages"][-1].content)


if __name__ == "__main__":
    main()
