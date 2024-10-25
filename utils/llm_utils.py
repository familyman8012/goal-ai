from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.memory import ConversationBufferWindowMemory
import os
from dotenv import load_dotenv
from langchain.callbacks.base import BaseCallbackHandler
from typing import Any, Dict, List

load_dotenv()


class StreamHandler(BaseCallbackHandler):
    def __init__(self, container, initial_text=""):
        self.container = container  # chat_message 객체를 직접 사용
        self.text = initial_text
        self.placeholder = self.container.empty()

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.text += token
        self.placeholder.markdown(self.text + "▌")

    def on_llm_end(self, *args, **kwargs) -> None:
        self.placeholder.markdown(self.text)


class LLMFactory:
    _memories = {}  # 각 세션별 메모리 저장을 위한 클래스 변수

    @staticmethod
    def get_memory(session_id: str, k: int = 5):
        """세션별 메모리 관리"""
        if session_id not in LLMFactory._memories:
            LLMFactory._memories[session_id] = ConversationBufferWindowMemory(
                k=k,
                return_messages=True,
                memory_key="chat_history",
            )
        return LLMFactory._memories[session_id]

    @staticmethod
    def create_llm(model_name: str):
        if model_name.startswith("gpt"):
            model_version = model_name.split("-", 1)[1]  # gpt-4o -> 4o
            return ChatOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name=f"gpt-{model_version}",  # gpt-4로 고정
                temperature=0.7,
                streaming=True,
            )
        elif model_name.startswith("claude"):
            model_version = model_name.split("-", 1)[
                1
            ]  # claude-3.5-sonnet -> 3.5-sonnet
            return ChatAnthropic(
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
                model_name=f"claude-{model_version}",
                temperature=0.7,
                streaming=True,
            )
        elif model_name.startswith("gemini"):
            model_version = model_name.split("-", 1)[1]  # gemini-pro -> pro
            return ChatGoogleGenerativeAI(
                google_api_key=os.getenv("GOOGLE_API_KEY"),
                model=f"gemini-{model_version}",
                temperature=0.7,
                streaming=False,  # 제미니는 스트리밍 비활성화
            )
        else:
            raise ValueError(f"지원하지 않는 모델입니다: {model_name}")

    @staticmethod
    def get_response(
        model_name: str,
        system_prompt: str,
        user_input: str,
        session_id: str,
        stream_handler: StreamHandler = None,
    ) -> str:
        memory = LLMFactory.get_memory(session_id)
        llm = LLMFactory.create_llm(model_name)

        messages = [SystemMessage(content=system_prompt)]
        chat_history = memory.chat_memory.messages
        messages.extend(chat_history)
        messages.append(HumanMessage(content=user_input))

        # 제미니 모델일 경우 스트리밍 없이 직접 표시
        if model_name.startswith("gemini"):
            response = llm.invoke(messages)
            if stream_handler:
                stream_handler.placeholder.markdown(response.content)
        else:
            if stream_handler:
                llm.callbacks = [stream_handler]
            response = llm.invoke(messages)

        memory.chat_memory.add_user_message(user_input)
        memory.chat_memory.add_ai_message(response.content)

        return response.content

    @staticmethod
    def single_get_response(
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        stream_handler: StreamHandler = None,
    ) -> str:
        llm = LLMFactory.create_llm(model_name)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        # 제미니 모델일 경우 스트리밍 없이 직접 표시
        if model_name.startswith("gemini"):
            response = llm.invoke(messages)
            if stream_handler:
                stream_handler.placeholder.markdown(response.content)
        else:
            if stream_handler:
                llm.callbacks = [stream_handler]
            response = llm.invoke(messages)

        return response.content
