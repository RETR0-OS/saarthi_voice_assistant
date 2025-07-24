from crewai import Agent
from crewai import LLM
from textwrap import dedent
from tools import DateTimeTool, GovernmentSchemeTool
from crewai_tools import DuckDuckGoSearchTool
from langchain_ollama import ChatOllama


"""
Creating Agents Cheat Sheet:
- Think like a boss. Work backwards from the goal and think which employee 
    you need to hire to get the job done.
- Define the Captain of the crew who orient the other agents towards the goal. 
- Define which experts the captain needs to communicate with and delegate tasks to.
    Build a top down structure of the crew.

Goal:
- Get a list of all government schemes and policies for which the user is elibigle to participate in

Captain/Manager/Boss:
- Expert Travel Agent

Employees/Experts to hire:
- City Selection Expert 
- Local Tour Guide


Notes:
- Agents should be results driven and have a clear goal in mind
- Role is their job title
- Goals should actionable
- Backstory should be their resume
"""

# This is an example of how to define custom agents.
# You can define as many agents as you want.
# You can also define custom tasks in tasks.py
class CustomAgents:

    # Class vars
    qwen_3 = LLM(
        model="ollama/qwen3:4b",
        base_url="http://localhost:11434"
    )

    def __init__(self, verbose=True):
        # self.OpenAIGPT4o = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.7)
        self.Ollama = ChatOllama(model="qwen3:4b")
        self.verbose = verbose  # Default to verbose

    @classmethod
    def create_govt_research_agent(cls):
        return Agent(
            role="Government Policy Researcher",
            goal="""Find and collect comprehensive information about active government schemes and policies',
        backstory='''You are an expert policy researcher with deep knowledge of government 
        operations and policy implementation. You specialize in finding the most current and 
        accurate information about government schemes from official sources.""",
            backstory="You are an experienced researcher with attention to detail",
            tools=[GovernmentSchemeTool(), DateTimeTool()],
            llm=cls.qwen_3,
            verbose=cls.verbose  # Enable logging for debugging
        )
    
    @classmethod
    def create_web_search_agent(cls):
        return Agent(
            role="Web Search Specialist",
            goal="Conduct web searches to find government schemes and policies",
            backstory=dedent("""
                You are a skilled web search specialist with expertise in finding 
                information on government schemes and policies. You excel at using 
                search engines and databases to locate relevant information quickly.
            """),
            tools=[DuckDuckGoSearchTool(), DateTimeTool()],
            llm=cls.qwen_3,
            verbose=cls.verbose  # Enable logging for debugging
        )
    