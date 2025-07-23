import os
from crewai import Agent, Task, Crew, Process
from langchain_ollama import ChatOllama
from dotenv import load_dotenv
# from textwrap import dedent
from agents import CustomAgents
from tasks import CustomTasks

# Install duckduckgo-search for this example:
# !pip install -U duckduckgo-search

from langchain.tools import DuckDuckGoSearchRun

search_tool = DuckDuckGoSearchRun()

load_dotenv()

# This is the main class that you will use to define your custom crew.
# You can define as many agents and tasks as you want in agents.py and tasks.py


class CustomCrew:

    def run(self):
        # Define your custom agents and tasks in agents.py and tasks.py
        agents = CustomAgents()
        tasks = CustomTasks()

        # Define your custom agents and tasks here
        research_agent = agents.create_research_agent()

        # Custom tasks include agent name and variables as input
        custom_task_1 = tasks.create_research_task("mid-day meal", "India")


        # Define your custom crew here
        crew = Crew(
            agents=[research_agent],
            tasks=[custom_task_1],
            verbose=True,
        )

        result = crew.kickoff()
        return result


# This is the main function that you will use to run your custom crew.
if __name__ == "__main__":
    custom_crew = CustomCrew()
    result = custom_crew.run()
    print("\n\n########################")
    print("## Here is you custom crew run result:")
    print("########################\n")
    print(result)
