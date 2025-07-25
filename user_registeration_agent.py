from langgraph_agent.utilities.IdentityManger import IdentityManagerSingleton
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

class PIIStoreState(TypedDict):
    """
    State to store PII data.
    """
    first_name: str = ""
    last_name: str = ""
    dob: str = ""
    phone: int = 0

class RegisterationState(TypedDict):
    """
    State to manage user registration.
    """
    registeration_status: bool = False




def get_PII(state: PIIStoreState) -> PIIStoreState:
    """
    Request PII registeration data from the user.
    """

    first_name = input("Enter your first name: ")
    last_name = input("Enter your last name: ")
    dob = input("Enter your date of birth (YYYY-MM-DD): ")
    phone = input("Enter your phone number: ")

    return {
        "first_name": first_name,
        "last_name": last_name,
        "dob": dob,
        "phone": phone
    }

def register_user(pii_state: PIIStoreState) -> RegisterationState:
    """
    Register a user using the indentity manager singleton.
    """
    
    identity_manager = IdentityManagerSingleton.get_instance()._identity_manager

    result = identity_manager.add_user(
        first_name=pii_state['first_name'],
        last_name=pii_state['last_name'],
        dob=pii_state['dob'],
        phone=pii_state['phone']
    )

    if not result["result"]:
        return {"registeration_status": False}
    print("User registered successfully.")
    return {"registeration_status": True}

graph_builder = StateGraph(RegisterationState, input_schema=PIIStoreState)


graph_builder.add_node("get_pii", get_PII)
graph_builder.add_node("register_user", register_user)

graph_builder.add_edge(START, "get_pii")
graph_builder.add_edge("get_pii", "register_user")
graph_builder.add_edge("register_user", END)

graph = graph_builder.compile()

print(graph.get_graph().draw_ascii())

result = graph.invoke({
    "first_name": "Aaditya",
    "last_name": "Jindal",
    "dob": "2000-01-01",
    "phone": 1234567890
})

print(result)