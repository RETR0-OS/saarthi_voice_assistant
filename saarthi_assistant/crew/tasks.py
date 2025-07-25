# To know more about the Task class, visit: https://docs.crewai.com/concepts/tasks
from crewai import Task
from .agents import CustomAgents
from textwrap import dedent


class CustomTasks:

    @staticmethod
    def __tip_section():
        return "If you do your BEST WORK, I'll give you a $10,000 commission!"

    @staticmethod
    def create_research_task(query: str, country: str):
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
            agent=agents.create_web_search_agent()
    )
    
    @staticmethod
    def create_user_authentication_task():
        """Task for authenticating a user through face recognition"""
        agents = CustomAgents()
        return Task(
            description=dedent("""
                Authenticate the user through face recognition:
                
                1. First check if user is already logged in using 'status' action
                2. If not logged in, use 'login' action to authenticate via face recognition
                3. Verify the authentication was successful using 'verify' action
                4. Report the authentication status
                
                Remember: You will not see any personal information, only success/failure status.
            """),
            expected_output="Authentication status report confirming whether user is logged in",
            agent=agents.create_identity_agent()
        )
    
    @staticmethod
    def create_pii_check_task(data_types: list):
        """Task for checking availability of PII data without accessing it"""
        agents = CustomAgents()
        return Task(
            description=dedent(f"""
                Check if the following PII data types are available for the authenticated user:
                {', '.join(data_types)}
                
                Steps:
                1. Ensure user is authenticated first
                2. For each data type, check if it exists in the secure vault
                3. Report which data types are available
                
                Important: You will only know if data exists, not the actual data content.
            """),
            expected_output="Report listing which PII data types are available in the vault",
            agent=agents.create_identity_agent()
        )
    
    @staticmethod
    def create_scheme_application_task(scheme_name: str, required_fields: dict):
        """Task for applying to a government scheme using secure PII data"""
        agents = CustomAgents()
        return Task(
            description=dedent(f"""
                Help user apply for the {scheme_name} government scheme:
                
                1. First verify user is authenticated
                2. Check if required PII data is available:
                   {', '.join(required_fields.keys())}
                3. For each required field, use the PII writer tool to securely fill the form:
                   - Field mappings: {required_fields}
                4. Confirm all fields have been filled successfully
                
                Remember: You cannot see the actual PII data, only confirm it was used successfully.
            """),
            expected_output=f"Confirmation that the {scheme_name} application form was filled with user's PII data",
            agent=agents.create_scheme_application_agent(),
            human_input=True
        )
    
    @staticmethod
    def create_user_enrollment_task():
        """Task for enrolling a new user"""
        agents = CustomAgents()
        return Task(
            description=dedent("""
                Initiate the enrollment process for a new user:
                
                1. Start the enrollment process
                2. Use the user enrollment tool to securely enroll the user
                3. Confirm when enrollment is complete
                
                Note: All personal information will be stored through a secure interface
                that you cannot access. You will only receive status updates.
            """),
            expected_output="Enrollment status report confirming if new user was successfully enrolled",
            agent=agents.create_identity_agent(),
            human_input=True
        )
    
    @staticmethod
    def create_secure_pii_storage_task(data_types_to_store: list):
        """Task for requesting PII data storage from user"""
        agents = CustomAgents()
        return Task(
            description=dedent(f"""
                Request the following PII data from the authenticated user for secure storage:
                {', '.join(data_types_to_store)}
                
                For each data type:
                1. Verify user is authenticated
                2. Send a secure request for the specific PII data
                3. Provide appropriate prompts explaining why the data is needed
                4. Wait for user to provide the data
                5. Confirm when the request has been sent
            """),
            expected_output="Status report confirming which PII data storage requests were sent to the user",
            agent=agents.create_identity_agent(),
            human_input=True
        )

    

