from langchain_community.chat_models import ChatLlamaCpp
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

@tool
def search_physics(query: str) -> str:
    """Search physics textbook"""
    return "Newton's second law is F = ma"

def test():
    llm = ChatLlamaCpp(
        model_path="models/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        n_ctx=2048,
        n_gpu_layers=0,
        n_threads=4,
        verbose=False,
    )
    
    try:
        llm_with_tools = llm.bind_tools([search_physics])
        msg = llm_with_tools.invoke([HumanMessage(content="What is Newton's law?")])
        print("Tools bound successfully!")
        print(msg)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()