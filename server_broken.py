"""
실험 02용 의도적으로 망가뜨린 MCP 서버
고의 결함 3가지:
  1. WRONG_DB_ID       : 존재하지 않는 DB ID → object_not_found 오류
  2. BAD_DESCRIPTION   : tool description이 너무 짧고 불명확 → 모델이 언제 써야 할지 모름
  3. NO_TIMEOUT        : timeout=0.001 초 → 항상 TimeoutException 발생
"""
import os
import httpx
from typing import Literal
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")

# 결함 1: 잘못된 DB ID (실제로 존재하지 않는 ID)
BROKEN_DB_ID = "00000000000000000000000000000000"

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

mcp = FastMCP("notion_summary_server_broken")


@mcp.tool()
async def save_summary_to_notion(
    title: str,
    content: str,
    source_url: str,
    category: Literal["paper", "stock_research", "stock_study"],
    sub_category: str = "",
    source: str = "",
    tags: list[str] | None = None,
    difficulty: str = "",
) -> str:
    # 결함 2: description 누락 — FastMCP는 docstring을 description으로 사용
    # docstring 없음 → 모델이 도구 목적을 추론 불가
    if not NOTION_API_KEY:
        return "오류: NOTION_API_KEY 없음"

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }

    payload = {
        "parent": {"database_id": BROKEN_DB_ID},  # 결함 1: 잘못된 DB ID
        "properties": {
            "Name": {"title": [{"type": "text", "text": {"content": title}}]}
        },
        "children": [{"object": "block", "type": "paragraph",
                       "paragraph": {"rich_text": [{"type": "text", "text": {"content": content[:1900]}}]}}],
    }

    try:
        # 결함 3: timeout=0.001 → 항상 TimeoutException
        async with httpx.AsyncClient(timeout=0.001) as client:
            response = await client.post(
                f"{NOTION_API_BASE}/pages",
                headers=headers,
                json=payload,
            )
        if response.status_code == 200:
            return f"저장 완료: {response.json().get('url', '')}"
        err = response.json()
        return (
            f"❌ 저장 실패 (HTTP {response.status_code})\n"
            f"코드: {err.get('code')}\n메시지: {err.get('message')}"
        )
    except httpx.TimeoutException:
        return "❌ 오류: 요청 시간 초과 (timeout=0.001s — 고의 결함)"
    except httpx.RequestError as e:
        return f"❌ 네트워크 오류: {e}"


if __name__ == "__main__":
    mcp.run()
