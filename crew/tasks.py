# To know more about the Task class, visit: https://docs.crewai.com/concepts/tasks
from crewai import Task
from agents import CustomAgents
from textwrap import dedent


class CustomTasks:
    def __tip_section(self):
        return "If you do your BEST WORK, I'll give you a $10,000 commission!"

    def create_research_task(self, query: str, country: str):
        agents = CustomAgents()
        return Task(
            description=f'''Research active government schemes and policies related to: {query}
            
            Focus on:
            1. Recently launched or announced schemes (2024-2025)
            2. Major policy updates or amendments
            3. Budget allocations and implementation timelines
            4. Target beneficiaries and eligibility criteria
            5. Application processes and contact information
            
            Country focus: {country}
            
            Prioritize official government sources and verified information.''',
            expected_output='Detailed list of active government schemes with comprehensive information',
            agent=agents.create_research_agent()
    )

    

