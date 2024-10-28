from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
from langchain.callbacks.base import BaseCallbackHandler
import streamlit as st

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
            # 스트리밍 설정
            if stream_handler and not model_name.startswith("gemini"):
                llm.callbacks = [stream_handler]
            
            # 메시지 생성
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
            
            # 응답 생성
            response = llm.invoke(messages)
            
            # 제미니 모델 처리
            if model_name.startswith("gemini") and stream_handler:
                stream_handler.placeholder.markdown(response.content)
            
            return response.content
                
        except Exception as e:
            error_msg = f"오류가 발생했습니다: {str(e)}"
            if stream_handler:
                stream_handler.placeholder.error(error_msg)
            return error_msg
