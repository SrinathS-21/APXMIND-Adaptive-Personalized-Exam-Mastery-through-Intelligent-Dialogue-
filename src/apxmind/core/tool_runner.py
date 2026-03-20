"""
Tool Execution Engine
=====================

Handles the dynamic LLM tool-calling loop for Llama 3.2.
Because LangChain's ChatLlamaCpp integration doesn't perfectly parse
Llama 3 tooling payloads, we implement the raw loop using the native
llama-cpp-python client.
"""

import json
import logging
from typing import Generator
from llama_cpp import Llama
from src.apxmind.core.tools import get_aneeta_tools
from src.apxmind.vectorstore.storage import ChromaDBManager

logger = logging.getLogger(__name__)

class AgenticToolRunner:
    def __init__(self, llm_instance: Llama):
        """Accepts the raw native llama_cpp Llama object (not the Langchain wrapper)"""
        self.llm = llm_instance
        self.tools = get_aneeta_tools()
        self.chroma = ChromaDBManager()

    def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        """Executes the mapped python function based on the LLM's selected tool."""
        
        # Determine the collection subject
        subject = None
        if tool_name == "search_ncert_biology":
            subject = "biology"
        elif tool_name == "search_ncert_chemistry":
            subject = "chemistry"
        elif tool_name == "search_ncert_physics":
            subject = "physics"
        else:
            return f"Error: Tool {tool_name} is not recognized by the system."

        # Fetch the exact collection
        query = arguments.get("query", "")
        # Yield status back to FastAPI so the React UI can say "Searching Biology Book..."
        logger.info(f"⚙️ Tool Activated: Searching {subject} for '{query}'")
        
        try:
            vectorstore = self.chroma.get_collection(subject)
            if not vectorstore:
                return f"Error: Could not load the {subject} vectorstore. Textbooks not found."
            
            # Retrieve documents
            retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
            docs = retriever.invoke(query)
            
            if not docs:
                return "Search completed, but no relevant textbook excerpts were found in the NCERT book."
                
            context = "\n\n".join([d.page_content for d in docs])
            return f"Found relevant excerpts from the NCERT {subject} curriculum:\n\n{context}"
            
        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}")
            return f"Error executing textbook search: {str(e)}"

    def chat_with_tools_stream(self, user_query: str, system_prompt: str) -> Generator[str, None, None]:
        """Runs the complete Tool-Calling Loop and yields token streams."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]
        
        # 1. First Inference (Check if model needs tools)
        response = self.llm.create_chat_completion(
            messages=messages,
            tools=self.tools,
            temperature=0.1 # Keep strict so it doesn't hallucinate arguments
        )
        
        message = response["choices"][0]["message"]
        
        # 2. Tool Execution Logic
        if "tool_calls" in message and message["tool_calls"]:
            # Yield a specialized status indicator so the UI knows a tool is running (Phase 4 bridge)
            yield json.dumps({"status": "running_tool", "message": "Flipping through NCERT book..."}) + "\n"
            
            messages.append(message) # Append the model's tool request
            
            for tool_call in message["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                args = json.loads(tool_call["function"]["arguments"])
                
                # Execute Python Function
                tool_result = self._execute_tool(tool_name, args)
                
                # Append exact result
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_name,
                    "content": tool_result
                })
            
            # 3. Final Inference (Convert facts into natural language)
            yield json.dumps({"status": "synthesizing", "message": "Writing final answer..."}) + "\n"
            
            final_stream = self.llm.create_chat_completion(
                messages=messages,
                temperature=0.7,
                stream=True
            )
            
            for chunk in final_stream:
                delta = chunk["choices"][0].get("delta", {})
                if "content" in delta:
                    # We yield pure text chunks now
                    yield delta["content"]
        else:
            # Did not use a tool. Just stream standard response.
            yield message.get("content", "")
