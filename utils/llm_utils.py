from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import streamlit as st
from dotenv import load_dotenv
import os
from langchain.callbacks.base import BaseCallbackHandler


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


class ChatMemory:
    def __init__(self, session_id: str, max_messages: int = 10):
        self.history_key = f"chat_history_{session_id}"
        self.max_messages = max_messages
        self.buffer_key = f"chat_buffer_{session_id}"

        # 세션 상태 초기화
        if self.history_key not in st.session_state:
            st.session_state[self.history_key] = []
        if self.buffer_key not in st.session_state:
            st.session_state[self.buffer_key] = []

    def add_message(self, role: str, content: str):
        # 메시지 객체 생성
        if role == "user":
            message = HumanMessage(content=content)
        elif role == "assistant":
            message = AIMessage(content=content)
        else:
            message = SystemMessage(content=content)

        # 시스템 메시지는 history의 첫 번째 위치에만 저장
        if isinstance(message, SystemMessage):
            if not st.session_state[self.history_key] or not isinstance(
                st.session_state[self.history_key][0], SystemMessage
            ):
                st.session_state[self.history_key].insert(0, message)
        else:
            # 일반 메시지는 버퍼에 추가
            st.session_state[self.buffer_key].append(message)
            if len(st.session_state[self.buffer_key]) > self.max_messages:
                self._move_to_history()

    def get_messages(self):
        # 시스템 메시지 + 버퍼의 메시지 반환
        system_messages = [
            msg
            for msg in st.session_state[self.history_key]
            if isinstance(msg, SystemMessage)
        ]
        return system_messages + st.session_state[self.buffer_key]

    def _move_to_history(self):
        # 버퍼의 절반을 요약하여 history로 이동
        messages_to_summarize = st.session_state[self.buffer_key][
            : (self.max_messages // 2)
        ]
        st.session_state[self.buffer_key] = st.session_state[self.buffer_key][
            (self.max_messages // 2) :
        ]

        if messages_to_summarize:
            summary = self._create_summary(messages_to_summarize)
            # 요약을 시스템 메시지 다음에 추가
            st.session_state[self.history_key].append(summary)

    def _create_summary(self, messages):
        summary_content = "이전 대화 요약:\n"
        for msg in messages:
            if isinstance(msg, HumanMessage):
                summary_content += f"사용자: {msg.content}\n"
            elif isinstance(msg, AIMessage):
                summary_content += f"AI: {msg.content}\n"
        return SystemMessage(content=summary_content)


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
        memory = ChatMemory(session_id)

        try:
            messages = memory.get_messages()

            # 시스템 메시지가 없거나 첫 번째가 아닌 경우에만 추가
            if not messages or not isinstance(messages[0], SystemMessage):
                memory.add_message("system", system_prompt)
                messages = memory.get_messages()

            # 사용자 메시지 추가
            memory.add_message("user", user_input)

            # 최신 메시지 목록 가져오기
            messages = memory.get_messages()

            # 응답 생성
            response = llm.invoke(
                messages,
                config={
                    "callbacks": (
                        [stream_handler]
                        if stream_handler
                        and not model_name.startswith("gemini")
                        else None
                    )
                },
            )

            # AI 응답 저장
            memory.add_message("assistant", response.content)

            return response.content

        except Exception as e:
            error_msg = f"오류가 발생했습니다: {str(e)}"
            if stream_handler:
                stream_handler.placeholder.error(error_msg)
            return error_msg
