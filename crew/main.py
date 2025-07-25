import os
from crewai import Agent, Task, Crew, Process
from langchain_ollama import ChatOllama
from dotenv import load_dotenv
# from textwrap import dedent
from .agents import CustomAgents
from .tasks import CustomTasks

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
    
    def run_identity_example(self):
        """Example of using identity management tools"""
        agents = CustomAgents()
        tasks = CustomTasks()
        
        # Create identity and application agents
        identity_agent = agents.create_identity_agent()
        scheme_agent = agents.create_scheme_application_agent()
        
        # Create tasks for secure identity management
        auth_task = tasks.create_user_authentication_task()
        
        # Check for specific PII data types
        pii_check_task = tasks.create_pii_check_task([
            "aadhaar", 
            "pan", 
            "phone", 
            "address"
        ])
        
        # Apply for a government scheme using secure PII
        application_task = tasks.create_scheme_application_task(
            scheme_name="PM Kisan Samman Nidhi",
            required_fields={
                "aadhaar": "aadhaar_number_field",
                "phone": "mobile_number_field",
                "address": "residential_address_field"
            }
        )
        
        # Create crew with identity management workflow
        identity_crew = Crew(
            agents=[identity_agent, scheme_agent],
            tasks=[auth_task, pii_check_task, application_task],
            verbose=True,
            process=Process.sequential  # Tasks run in order
        )
        
        result = identity_crew.kickoff()
        return result
    
    def run_enrollment_example(self):
        """Example of enrolling a new user"""
        agents = CustomAgents()
        tasks = CustomTasks()
        
        identity_agent = agents.create_identity_agent()
        
        # Enrollment and PII storage tasks
        enrollment_task = tasks.create_user_enrollment_task()
        pii_storage_task = tasks.create_secure_pii_storage_task([
            "aadhaar",
            "pan",
            "phone",
            "address"
        ])
        
        enrollment_crew = Crew(
            agents=[identity_agent],
            tasks=[enrollment_task, pii_storage_task],
            verbose=True,
            process=Process.sequential
        )
        
        result = enrollment_crew.kickoff()
        return result
