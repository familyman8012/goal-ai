from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import streamlit as st
from dotenv import load_dotenv
import os
from langchain.callbacks.base import BaseCallbackHandler


def get_api_key(key_name: str) -> str:
    api_key = None
    if hasattr(st, "secrets"):  # Streamlit Cloud 환경
        try:
            api_key = st.secrets["api_keys"][key_name]
        except KeyError:
            raise ValueError(
                f"Streamlit secrets에서 {key_name}를 찾을 수 없습니다."
            )
    else:  # 로컬 환경
        load_dotenv()
        api_key = os.getenv(key_name)

    if not api_key:
        raise ValueError(f"{key_name} API 키가 설정되지 않았습니다.")

    return api_key


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
    def __init__(self, session_id: str, max_pairs: int = 3):
        self.history_key = f"chat_history_{session_id}"
        self.max_pairs = max_pairs
        self.buffer_key = f"chat_buffer_{session_id}"
        self.display_key = f"chat_display_{session_id}"

        # 세션 상태 초기화
        if self.history_key not in st.session_state:
            st.session_state[self.history_key] = []
        if self.buffer_key not in st.session_state:
            st.session_state[self.buffer_key] = []
        if self.display_key not in st.session_state:
            st.session_state[self.display_key] = []

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
            # 일반 메시지는 버퍼와 display에 추가
            st.session_state[self.buffer_key].append(message)
            st.session_state[self.display_key].append(message)

            # 버퍼의 메시지 쌍 수 계산 (user-ai 쌍)
            message_pairs = len(st.session_state[self.buffer_key]) // 2

            # 대화 쌍이 max_pairs를 초과하면 요약
            if message_pairs >= self.max_pairs:
                self._move_to_history()

    def get_messages(self):
        # LLM용 메시지 (요약 포함)
        all_messages = []

        # 시스템 메시지 추가
        for msg in st.session_state[self.history_key]:
            if isinstance(msg, SystemMessage):
                all_messages.append(msg)
                break

        # 요약된 메시지 추가
        for msg in st.session_state[self.history_key]:
            if (
                isinstance(msg, AIMessage)
                and "[이전 대화 요약]" in msg.content
            ):
                all_messages.append(msg)

        # 현재 버퍼의 메시지들 추가
        all_messages.extend(st.session_state[self.buffer_key])

        return all_messages

    def get_display_messages(self):
        # UI 표시 메시지 (전체 대화 내역)
        return st.session_state[self.display_key]

    def _move_to_history(self):
        # 버퍼의 모든 메시지를 한번에 요약
        messages_to_summarize = st.session_state[self.buffer_key]
        # 버퍼 비우기
        st.session_state[self.buffer_key] = []

        if messages_to_summarize:
            summary = self._create_summary(messages_to_summarize)
            # 요약을 AIMessage로 변환
            summary_message = AIMessage(content=f"[이전 대화 요약] {summary}")

            # history에 추가 (시스템 메시지는 유지하고 그 다음에 요약 추가)
            new_history = []
            system_messages_added = False

            # 먼저 시스템 메시지들을 추가
            for msg in st.session_state[self.history_key]:
                if isinstance(msg, SystemMessage):
                    new_history.append(msg)
                else:
                    if not system_messages_added:
                        new_history.append(summary_message)
                        system_messages_added = True
                    new_history.append(msg)

            # 시스템 메시지가 없었던 경우 마지막에 추가
            if not system_messages_added:
                new_history.append(summary_message)

            st.session_state[self.history_key] = new_history

    def _create_summary(self, messages):
        try:
            # 대화 내용을 구조화된 형태로 구성
            conversation_parts = []
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    conversation_parts.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    conversation_parts.append({"role": "assistant", "content": msg.content})

            # 요약을 위한 프롬프트 구성
            summary_prompt = """
            다음 대화 내용을 150자 이내로 핵심만 간단히 요약해주세요:

            {conversation}
            
            요약 형식:
            현재까지의 대화를 사용자와 ai 가 무슨 대화를 했었는지 핵심만 요약해주세요.
            
            주의사항:
            1. 150자를 넘지 않도록 할 것
            2. 중요 키워드는 반드시 포함할 것
            3. 구체적인 수치나 날짜는 유지할 것
            """

            # 대화 내용을 프롬프트에 포함
            conversation_text = "\n".join([
                f"{'사용자' if msg['role'] == 'user' else 'AI'}: {msg['content']}"
                for msg in conversation_parts
            ])

            # 요약을 위해 Gemini-Flash 모델 사용
            llm = LLMFactory.create_llm("gemini-1.5-flash-latest")
            response = llm.invoke([
                HumanMessage(content=summary_prompt.format(conversation=conversation_text))
            ])
            
            # 임시 UI로 요약 과정 표시
            with st.expander("🔍 요약 디버그"):
                st.write("### 현재 요약 과정")
                st.write("원본 대화:")
                st.write(conversation_text)
                st.write("---")
                st.write("새로운 요약 결과 (Gemini-Flash):")
                st.write(response.content)
                
                st.write("\n### 전체 대화 컨텍스트")
                st.write("시스템 메시지:")
                for msg in st.session_state[self.history_key]:
                    if isinstance(msg, SystemMessage):
                        st.write(msg.content)
                
                st.write("\n요약된 이전 대화:")
                for msg in st.session_state[self.history_key]:
                    if isinstance(msg, AIMessage) and "[이전 대화 요약]" in msg.content:
                        st.write(msg.content)
                
                st.write("\n현재 버퍼의 대화:")
                for msg in st.session_state[self.buffer_key]:
                    role = "사용자" if isinstance(msg, HumanMessage) else "AI"
                    st.write(f"{role}: {msg.content}")
       
                
            # 응답 검증 강화
            summary = response.content
            if not summary or len(summary) < 10:
                raise ValueError("응답이 너무 짧습니다")
            
            if len(summary) > 400:  # 200자 제한의 2배까지 허용
                raise ValueError("응답이 너무 깁니다")
            

            
            # 핵 키워드 포함 여부 검증 (옵션)
            # important_keywords = self._extract_keywords(messages)
            # if not any(keyword in summary for keyword in important_keywords):
            #     raise ValueError("중요 키워드가 누락되었습니다")
            
            return summary

        except Exception as e:
            st.warning(f"요약 생성 실패: {str(e)}")
            return self._create_fallback_summary(messages)

    def _create_fallback_summary(self, messages):
        fallback_summary = "대화 요약:\n"
        for msg in messages[-2:]:  # 마지막 2개 메시지만 포함
            role = "사용자" if isinstance(msg, HumanMessage) else "AI"
            content = msg.content
            if len(content) > 50:
                content = content[:47] + "..."
            fallback_summary += f"- {role}: {content}\n"
        
        return fallback_summary


class LLMFactory:
    @staticmethod
    def create_llm(model_name: str):
        try:
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
                api_key = get_api_key("GOOGLE_API_KEY")
                if not api_key:
                    raise ValueError("Google API 가 설정되지 않았습니다.")

                model_version = model_name.split("-", 1)[1]
                llm = ChatGoogleGenerativeAI(
                    google_api_key=api_key,
                    model=f"gemini-{model_version}",  # 모델명 동적 설정
                    temperature=0.7,
                    streaming=False,  # Gemini는 스트리밍 미지원
                )

                return llm

            else:
                raise ValueError(f"지원하지 않는 모델입니다: {model_name}")

        except Exception as e:
            error_msg = f"LLM 초기화 중 오류 발생: {str(e)}"
            st.error(error_msg)
            raise Exception(error_msg)

    @staticmethod
    def get_response(
        model_name: str,
        system_prompt: str,
        user_input: str,
        session_id: str,
        stream_handler: StreamHandler = None,
    ) -> str:
        try:
            llm = LLMFactory.create_llm(model_name)
            memory = ChatMemory(session_id)
            messages = memory.get_messages()

            # 제미니 모델을 위한 특별 처리
            if model_name.startswith("gemini"):
                try:
                    # 기존 메시지 히스토리 활용하도록 수정
                    if not messages or not isinstance(messages[0], SystemMessage):
                        memory.add_message("system", system_prompt)
                        messages = memory.get_messages()

                    # 사용자 메시지 추가
                    memory.add_message("user", user_input)
                    messages = memory.get_messages()

                    # 메시지 형식을 Gemini용으로 변환
                    gemini_messages = []
                    for msg in messages:
                        if isinstance(msg, SystemMessage):
                            gemini_messages.append(
                                HumanMessage(content=f"시스템 설정: {msg.content}")
                            )
                        elif isinstance(msg, HumanMessage):
                            gemini_messages.append(msg)
                        elif isinstance(msg, AIMessage):
                            gemini_messages.append(msg)

                    # 응답 생성 시도
                    response = llm.invoke(gemini_messages)

                    # 응답 표시 (스트리밍 대신 직접 표시)
                    if stream_handler:
                        stream_handler.placeholder.empty()
                        stream_handler.container.markdown(response.content)

                    # AI 응답 저장
                    memory.add_message("assistant", response.content)
                    return response.content

                except Exception as gemini_error:
                    st.error(f"Gemini 처리 중 오류: {str(gemini_error)}")
                    raise gemini_error

            else:
                # 기존 로직 (다른 모델들)
                if not messages or not isinstance(messages[0], SystemMessage):
                    memory.add_message("system", system_prompt)
                    messages = memory.get_messages()
                memory.add_message("user", user_input)
                messages = memory.get_messages()

                response = llm.invoke(
                    messages,
                    config={"callbacks": ([stream_handler] if stream_handler else None)}
                )

                # AI 응답 저장
                memory.add_message("assistant", response.content)
                return response.content

        except Exception as e:
            error_msg = f"오류가 발생했습니다: {str(e)}"
            if stream_handler:
                stream_handler.placeholder.error(error_msg)
            st.error(f"상세 오류: {str(e)}")
            return f"죄송합니다. 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (에러: {str(e)})"
