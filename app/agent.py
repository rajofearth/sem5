import json
import os
from PyQt5.QtCore import QObject, pyqtSignal
from cerebras.cloud.sdk import Cerebras
from app import tools

SYSTEM_PROMPT = (
    '''
    Be concise with your responses. Only use plain text with basic formatting. No markdown.
    '''
)
MODEL_DEFAULT = 'gemma-4-31b'
MAX_ROUNDS = 8


class ChatWorker(QObject):
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)
    tool_started = pyqtSignal(str, str)

    def __init__(self, prompt, model):
        super().__init__()
        self.prompt = prompt
        self.model = model
        self.stop_requested = False

    def stop(self):
        self.stop_requested = True

    def run(self):
        try:
            client = Cerebras(api_key=os.environ['CEREBRAS_API_KEY'])
            messages = [
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': self.prompt},
            ]
            for _ in range(MAX_ROUNDS):
                if self.stop_requested:
                    self.finished.emit('Agent stopped.')
                    return
                response = client.chat.completions.create(
                    model=self.model, messages=messages, tools=tools.schemas(),
                )
                message = response.choices[0].message
                tool_calls = message.tool_calls or []
                messages.append(message.model_dump(exclude_none=True))
                if not tool_calls:
                    self.finished.emit(message.content or '')
                    return
                for call in tool_calls:
                    if self.stop_requested:
                        self.finished.emit('Agent stopped.')
                        return
                    try:
                        arguments = json.loads(call.function.arguments)
                    except (ValueError, TypeError):
                        arguments = {}
                    self.tool_started.emit(tools.label(call.function.name), tools.detail(call.function.name, arguments))
                    try:
                        result = tools.execute(call.function.name, arguments)
                    except (KeyError, TypeError, ValueError) as error:
                        result = f'Tool input error: {error}'
                    messages.append({
                        'role': 'tool', 'tool_call_id': call.id, 'content': result,
                    })
            self.failed.emit('The model used too many tool calls without producing an answer.')
        except Exception as error:
            self.failed.emit(str(error))
