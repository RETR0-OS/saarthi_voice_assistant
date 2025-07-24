from crewai.tools import BaseTool
from langchain_community.tools import DuckDuckGoSearchRun
import datetime

class GovernmentSchemeTool(BaseTool):
    name: str ="government_scheme_search"
    description: str ="Search for active government schemes and policies from official sources"
    def _run(self, query: str, country: str = 'India') -> str:
        search = DuckDuckGoSearchRun()
        official_queries = [
            f"{query} site:gov.in {country} 2024 2025",
            f"{query} government scheme policy {country} active",
            f"{query} ministry {country} latest announcement"
        ]
        
        results = []
        for q in official_queries:
            try:
                result = search.run(q)
                results.append(result)
            except Exception as e:
                results.append(f"Search error: {str(e)}")
        
        return "\n\n".join(results)
    

class DateTimeTool(BaseTool):
    name: str = "datetime_tool"
    description: str = "Get the current date and time in UTC format"

    def _run(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    