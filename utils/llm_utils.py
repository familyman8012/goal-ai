from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_message_histories import (
    StreamlitChatMessageHistory,
)
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
import os
from dotenv import load_dotenv
from langchain.callbacks.base import BaseCallbackHandler
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


# 환경 변수 가져오기 함수
def get_api_key(key_name: str) -> str:
    if hasattr(st, "secrets"):  # Streamlit Cloud 환경
        return st.secrets["api_keys"][key_name]
    else:  # 로컬 환경
        load_dotenv()
        return os.getenv(key_name)


class StreamHandler(BaseCallbackHandler):
    def __init__(self, container, initial_text=""):
        self.container = container
        self.text = initial_text
        self.placeholder = self.container.empty()

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.text += token
        self.placeholder.markdown(self.text + "▌")

    def on_llm_end(self, *args, **kwargs) -> None:
        self.placeholder.markdown(self.text)


class HybridChatMemory:
    def __init__(self, session_id: str, window_size: int = 5):
        self.history_key = f"chat_history_{session_id}"
        self.summary_key = f"chat_summary_{session_id}"

        # StreamlitChatMessageHistory 초기화
        if self.history_key not in st.session_state:
            st.session_state[self.history_key] = StreamlitChatMessageHistory(
                key=self.history_key
            )

        # 버퍼 메모리 초기화 (최근 N개 메시지만 유지)
        self.buffer_memory = ConversationBufferWindowMemory(k=window_size)

        # 요약 저장소
        if self.summary_key not in st.session_state:
            st.session_state[self.summary_key] = ""

    def add_message(self, message):
        # 메시지 객체 생성
        if message["role"] == "user":
            msg = HumanMessage(content=message["content"])
        elif message["role"] == "assistant":
            msg = AIMessage(content=message["content"])
        else:
            msg = SystemMessage(content=message["content"])

        # StreamlitChatMessageHistory에 메시지 추가
        st.session_state[self.history_key].add_message(msg)

        # 버퍼 메모리 업데이트
        if (
            len(st.session_state[self.history_key].messages)
            > self.buffer_memory.k
        ):
            # 오래된 메시지 요약
            messages_to_summarize = st.session_state[
                self.history_key
            ].messages[: -self.buffer_memory.k]
            self._update_summary(messages_to_summarize)

            # 최근 메시지만 버퍼에 유지
            recent_messages = st.session_state[self.history_key].messages[
                -self.buffer_memory.k :
            ]
            self.buffer_memory.clear()
            for msg in recent_messages:
                if isinstance(msg, HumanMessage):
                    self.buffer_memory.save_context(
                        {"input": msg.content}, {"output": ""}
                    )
                elif isinstance(msg, AIMessage):
                    self.buffer_memory.save_context(
                        {"input": ""}, {"output": msg.content}
                    )

    def _update_summary(self, messages):
        # 요약 생성 로직
        llm = LLMFactory.create_llm(st.session_state.selected_model)
        summary_prompt = f"""
        다음 대화 내용을 간단히 요약해주세요:
        {[msg.content for msg in messages]}
        """
        summary = llm.predict(summary_prompt)
        st.session_state[self.summary_key] = summary

    def get_context(self):
        return {
            "summary": st.session_state[self.summary_key],
            "recent_messages": self.buffer_memory.load_memory_variables({})[
                "history"
            ],
        }


class LLMFactory:
    @staticmethod
    def create_llm(model_name: str):
        if model_name.startswith("gpt"):
            model_version = model_name.split("-", 1)[1]
            return ChatOpenAI(
                api_key=get_api_key("OPENAI_API_KEY"),
                model_name=f"gpt-{model_version}",
                temperature=0.7,
                streaming=True,
            )
        elif model_name.startswith("claude"):
            model_version = model_name.split("-", 1)[1]
            return ChatAnthropic(
                anthropic_api_key=get_api_key("ANTHROPIC_API_KEY"),
                model_name=f"claude-{model_version}",
                temperature=0.7,
                streaming=True,
            )
        elif model_name.startswith("gemini"):
            model_version = model_name.split("-", 1)[1]
            return ChatGoogleGenerativeAI(
                google_api_key=get_api_key("GOOGLE_API_KEY"),
                model=f"gemini-{model_version}",
                temperature=0.7,
                streaming=False,
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
        llm = LLMFactory.create_llm(model_name)

        try:
            # 하이브리드 메모리 초기화
            memory = HybridChatMemory(session_id)
            context = memory.get_context()

            # 시스템 프롬프트에 컨텍스트 포함
            full_system_prompt = f"""
            {system_prompt}

            이전 대화 요약:
            {context['summary']}

            최근 대화:
            {context['recent_messages']}
            """

            # 프롬프트 템플릿 생성 (시스템 메시지를 맨 앞에 배치)
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        full_system_prompt,
                    ),  # 시스템 메시지를 하나로 통합
                    ("human", "{input}"),
                ]
            )

            # 응답 생성
            chain = prompt | llm
            response = chain.invoke(
                {"input": user_input},
                config={
                    "callbacks": (
                        [stream_handler]
                        if stream_handler
                        and not model_name.startswith("gemini")
                        else None
                    )
                },
            )

            # 메시지 저장
            memory.add_message({"role": "user", "content": user_input})
            memory.add_message(
                {"role": "assistant", "content": response.content}
            )

            return response.content

        except Exception as e:
            error_msg = f"오류가 발생했습니다: {str(e)}"
            if stream_handler:
                stream_handler.placeholder.error(error_msg)
            return error_msg
