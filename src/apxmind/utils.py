from typing import List
from langchain_core.messages import AnyMessage, HumanMessage

def get_last_human_message(messages: List[AnyMessage]) -> str:
    """Extracts the content of the last human message from a list of messages."""
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return message.content
    return ""