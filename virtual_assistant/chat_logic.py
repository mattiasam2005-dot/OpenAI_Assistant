from dataclasses import dataclass
from typing import Optional
import json

import resend
from openai import OpenAI


@dataclass
class Message:
    role: str
    content: str


class ChatLogic:
    def __init__(self, openai_key: str, resend_key: str, assistant_id: str):
        self.client = OpenAI(api_key=openai_key)
        resend.api_key = resend_key
        self.assistant_id = assistant_id
        self.thread_id = None

    def initialize_thread(self):
        if not self.thread_id:
            thread = self.client.beta.threads.create()
            self.thread_id = thread.id

        return self.thread_id

    def send_email(self, name: str, email: str) -> str:
        try:
            resend.Emails.send(
                {
                    "from": "onboarding@resend.dev",
                    "to": email,
                    "subject": "Benvenuto in CinePass Italia",
                    "html": f"""
                    <p>Ciao {name},</p>
                    <p>Benvenuto in CinePass Italia!</p>
                    <p>Abbiamo ricevuto la tua richiesta di informazioni.</p>
                    <p>Cordiali saluti,<br>CinePass Italia</p>
                    """,
                }
            )
            return "Email inviata correttamente."
        except Exception as e:
            return f"Errore durante l'invio dell'email: {e}"

    def handle_function_calls(self, run, thread_id: str):
        tool_calls = run.required_action.submit_tool_outputs.tool_calls
        tool_outputs = []

        for tool in tool_calls:
            function_name = tool.function.name
            function_args = json.loads(tool.function.arguments)

            if function_name == "send_email":
                output = self.send_email(**function_args)
            else:
                output = f"Funzione non riconosciuta: {function_name}"

            tool_outputs.append(
                {
                    "tool_call_id": tool.id,
                    "output": output,
                }
            )

        try:
            return self.client.beta.threads.runs.submit_tool_outputs_and_poll(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tool_outputs,
            )
        except Exception:
            return None

    def process_message(self, user_message: str) -> Optional[str]:
        thread_id = self.initialize_thread()

        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message,
        )

        run = self.client.beta.threads.runs.create_and_poll(
            thread_id=thread_id,
            assistant_id=self.assistant_id,
        )

        while run.status != "completed":
            if run.status == "requires_action":
                run = self.handle_function_calls(run, thread_id)

                if not run:
                    return None
            elif run.status in {"failed", "cancelled", "expired"}:
                return None
            else:
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id,
                )

        messages = self.client.beta.threads.messages.list(
            thread_id=thread_id
        )

        for message in messages.data:
            if message.run_id == run.id and message.role == "assistant":
                return message.content[0].text.value

        return None

    def fetch_messages(self, thread_id: str):
        return self.client.beta.threads.messages.list(thread_id=thread_id)
