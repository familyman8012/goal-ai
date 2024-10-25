import requests
import os
from dotenv import load_dotenv

load_dotenv()

def search_with_pplx(query: str) -> str:
    """PPLX API를 사용하여 검색을 수행하는 함수"""
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {os.getenv('PPLX_API_KEY')}"
    }
    
    payload = {
        "model": "llama-3.1-sonar-small-128k-online",
        "messages": [
            {
                "role": "system",
                "content": "당신은 검색 전문가입니다. 사용자의 검색어에 대해 최신의 정확한 정보를 제공합니다. 답변은 명확하고 구체적이어야 하며, 가능한 한 최신 정보를 포함해야 합니다."
            },
            {
                "role": "user",
                "content": f"다음 주제에 대해 최신 정보를 알려주세요: {query}"
            }
        ]
    }
    
    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        
        # "Perplexity 검색결과입니다:" 텍스트 추가
        return "Perplexity 검색결과입니다:\n\n" + result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"검색 중 오류가 발생했습니다: {str(e)}"
