import os

import chainlit as cl
from dotenv import load_dotenv

from chat_logic import ChatLogic

load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_KEY")
RESEND_KEY = os.getenv("RESEND_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")


@cl.on_chat_start
def on_chat_start():
    chat_logic = ChatLogic(
        openai_key=OPENAI_KEY,
        resend_key=RESEND_KEY,
        assistant_id=ASSISTANT_ID,
    )
    cl.user_session.set("chat_logic", chat_logic)


@cl.on_message
async def main(message: cl.Message):
    chat_logic = cl.user_session.get("chat_logic")

    if chat_logic is None:
        await cl.Message(
            author="assistant",
            content="La sessione non è stata inizializzata correttamente.",
        ).send()
        return

    response = chat_logic.process_message(message.content)

    await cl.Message(
        author="assistant",
        content=response or "Non sono riuscito a ottenere una risposta.",
    ).send()
