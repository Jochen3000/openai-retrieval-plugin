from fastapi import APIRouter, Body, HTTPException
from typing import Dict
import openai

prompt_router = APIRouter()

# Add a global variable to store conversation history
conversation_history = [
    {"role": "system", "content": "You are a helpful assistant."}
]

# Add a constant for maximum memory tokens
MAX_MEMORY_TOKENS = 70

@prompt_router.post("/prompt")
async def chat_endpoint(body: Dict[str, str] = Body(...)):
    user_message = body.get("user_message")
    if not user_message:
        raise HTTPException(status_code=400, detail="user_message is required")

    conversation_history.append({"role": "user", "content": user_message})

    response = openai.ChatCompletion.create(
        model="gpt-4", # OR gpt-3.5-turbo
        messages=conversation_history,
    )

    assistant_message = response.choices[0].message["content"]
    conversation_history.append({"role": "assistant", "content": assistant_message})

    # Remove older messages when total tokens in conversation_history exceed MAX_MEMORY_TOKENS
    while response.usage['total_tokens'] > MAX_MEMORY_TOKENS:
        # Ensure that there are at least two messages (one "system" and one other message) before removing a message
        if len(conversation_history) > 2:
            removed_message = conversation_history.pop(1)  # Skip the "system" message at index 0
            # Create a new API call without the removed_message
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=conversation_history,
            )
        else:
            break

    return assistant_message



