import json
import json
from llama_cpp import Llama
from src.apxmind.core.tools import get_aneeta_tools

def test_tool_calling():
    print("Loading model...")
    llm = Llama(
        model_path="models/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        n_ctx=2048,
        n_gpu_layers=0,
        n_threads=4,
        verbose=False,
        chat_format="chatml-function-calling"
    )
    
    tools = get_aneeta_tools()
    
    messages = [
        {"role": "system", "content": "You are a helpful educational tutor. Use the provided tools to search the textbooks if you need factual science information."},
        {"role": "user", "content": "Can you check the physics book for Newton's second law?"}
    ]
    
    print("\nSending prompt to model...")
    print(f"User: {messages[1]['content']}")
    response = llm.create_chat_completion(
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.1
    )
    
    response_msg = response["choices"][0]["message"]
    if "tool_calls" in response_msg and response_msg["tool_calls"]:
        print("\nSUCCESS! The model successfully emitted a tool call:")
        for t in response_msg["tool_calls"]:
            func_name = t["function"]["name"]
            args = json.loads(t["function"]["arguments"])
            print(f"- Selected Tool: {func_name}")
            print(f"- Arguments: {args}")
    else:
        print("\nFAILURE! The model responded with normal text instead of a tool call:")
        print(response_msg.get("content", ""))

if __name__ == "__main__":
    test_tool_calling()
