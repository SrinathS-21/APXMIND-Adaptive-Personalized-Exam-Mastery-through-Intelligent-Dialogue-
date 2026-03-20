"""
Tool Schemas for LLM Routing
============================

Definitions of external tools available to the Llama 3.2 model.
These functions allow the AI to actively decide when to query 
the vector database, instead of forcing standard RAG.
"""

from pydantic import BaseModel, Field
from typing import List, Dict

# 1. Define the input schemas using Pydantic
class SearchNCERTBiology(BaseModel):
    """Search the NEET Biology textbook and curriculum."""
    query: str = Field(description="The scientific topic or biological term to search for (e.g., 'Mitochondria function' or 'Mitosis phases').")

class SearchNCERTChemistry(BaseModel):
    """Search the NEET Chemistry textbook and curriculum."""
    query: str = Field(description="The chemical topic or equation to search for (e.g., 'Thermodynamics laws' or 'SN1 Reaction').")

class SearchNCERTPhysics(BaseModel):
    """Search the NEET Physics textbook and curriculum."""
    query: str = Field(description="The physical concept or formula to search for (e.g., 'Newton laws' or 'Kinematics').")


# 2. Define standard OpenAI/LLama compatible JSON Schemas
def get_aneeta_tools() -> List[Dict]:
    """
    Returns the JSON schemas for the available tools.
    The LLM uses these to determine IF and HOW it should fetch context.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "search_ncert_biology",
                "description": "Search the local vector database containing the official NCERT Biology textbook for NEET.",
                "parameters": SearchNCERTBiology.model_json_schema()
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_ncert_chemistry",
                "description": "Search the local vector database containing the official NCERT Chemistry textbook for NEET.",
                "parameters": SearchNCERTChemistry.model_json_schema()
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_ncert_physics",
                "description": "Search the local vector database containing the official NCERT Physics textbook for NEET.",
                "parameters": SearchNCERTPhysics.model_json_schema()
            }
        }
    ]
