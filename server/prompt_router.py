from fastapi import APIRouter, Request, Body, HTTPException
from typing import Dict
import openai

prompt_router = APIRouter()

# Store conversation histories in a dictionary
conversation_histories = {}

# Add a constant for maximum memory tokens
MAX_MEMORY_TOKENS = 70

@prompt_router.post("/prompt")
async def chat_endpoint(user_id: str, body: Dict[str, str] = Body(...)):
    # Check if user_id exists in conversation_histories, if not, create a new history
    if user_id not in conversation_histories:
        conversation_histories[user_id] = [{"role": "system", "content": "You are a helpful assistant."}]

    user_message = body.get("user_message")
    if not user_message:
        raise HTTPException(status_code=400, detail="user_message is required")

    conversation_histories[user_id].append({"role": "user", "content": user_message})

    response = openai.ChatCompletion.create(
        model="gpt-4", # OR gpt-3.5-turbo
        messages=conversation_histories[user_id],
    )

    assistant_message = response.choices[0].message["content"]
    conversation_histories[user_id].append({"role": "assistant", "content": assistant_message})

    # Remove older messages when total tokens in conversation_history exceed MAX_MEMORY_TOKENS
    while response.usage['total_tokens'] > MAX_MEMORY_TOKENS:
        # Ensure that there are at least two messages (one "system" and one other message) before removing a message
        if len(conversation_histories[user_id]) > 2:
            removed_message = conversation_histories[user_id].pop(1)  # Skip the "system" message at index 0
            # Create a new API call without the removed_message
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=conversation_histories[user_id],
            )
        else:
            break

    return assistant_message




