# from ..identity_wallet.identity_manager.identity_manager import IdentityManager
from langgraph.graph import START, END, StateGraph, add_messages
from typing_extensions import TypedDict
from typing import Annotated, Any, Dict, List, Optional, Union, Literal
from langgraph.types import interrupt, Command


class State(TypedDict):    
    # identity_manager: IdentityManager
    authentication_status: bool
    authentication_attempts: int

class UserRegisterationData(TypedDict):
    first_name: str
    last_name: str
    phone: Optional[str]
    dob: Optional[str]


# Router
def check_login(state: State) -> bool:
    """
    Check if the user is already logged in.
    """
    return state["authentication_status"]

# def login_user(state: State) -> State:
#     """
#     Login the user.
#     """

#     result = state["identity_manager"].login()

#     if result["result"]:
#         state["authentication_status"] = True
#         state["authentication_attempts"] = 0
#     else:
#         state["authentication_attempts"] += 1
#         state["authentication_status"] = False
#     return state

def register_user(state: State) -> UserRegisterationData:
    """
    Register a new user.
    """
    first_name = interrupt("Please enter your first name:")
    last_name = interrupt("Please enter your last name:")
    phone = interrupt("Please enter your phone number:")
    dob = interrupt("Please enter your date of birth:")

    print("User Registration Data:")
    print(f"First Name: {first_name}")
    print(f"Last Name: {last_name}")
    print(f"Phone: {phone}")
    print(f"DOB: {dob}")

    return {
        "first_name": first_name,
        "last_name": last_name,
        "phone": phone,
        "dob": dob
    }

graph_builder = StateGraph(State, output_schema=UserRegisterationData)

graph_builder.add_node(
    "check_login",
    lambda state: state,
)
graph_builder.add_node(
    "register_user",
    register_user,
)

graph_builder.add_edge(
    START,
    "check_login",
)
graph_builder.add_conditional_edges(
    "check_login",
    check_login,
    {
        True: "register_user",
        False: END,
    },
)
graph_builder.add_edge(
    "check_login",
    "register_user",
)
graph_builder.add_edge(
    "register_user",
    END,
)

graph = graph_builder.compile()

result = graph.invoke(input={
    "authentication_status": True,
    "authentication_attempts": 0,
    # "identity_manager": IdentityManager(),
})

print("Graph Result:", result)