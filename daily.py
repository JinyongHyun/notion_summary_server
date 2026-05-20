"""daily.py — 오늘 날짜 페이지가 없을 때만 Notion에 저장"""
import asyncio, sys, io, httpx, xml.etree.ElementTree as ET, os
from datetime import datetime
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
load_dotenv('d:/python/notion_summary_server/.env')
sys.path.insert(0, 'd:/python/notion_summary_server')

TODAY = datetime.now().strftime("%Y-%m-%d")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}
DB = {
    "paper":          os.getenv("NOTION_PAPER_DB_ID",          "34617b872be68060a474e18a73510f38"),
    "stock_research": os.getenv("NOTION_STOCK_RESEARCH_DB_ID", "39bf50a1aca04ad2a10079e958cf96d4"),
    "stock_study":    os.getenv("NOTION_STOCK_STUDY_DB_ID",    "d1afcb876857487eb978c1a8e0952d05"),
}

# 오늘 저장할 5개 항목 정의
ITEMS = [
    {"label": "① AI 논문",       "db": "paper",          "check": f"[{TODAY}]"},
    {"label": "② 뉴스 종합",     "db": "stock_research", "check": f"[{TODAY}] 경제 뉴스 종합"},
    {"label": "③ 주간브리핑",    "db": "stock_research", "check": f"[{TODAY}] 주간 투자 브리핑"},
    {"label": "④ 증권사리포트",  "db": "stock_research", "check": f"[{TODAY}] 섹터 분석 리포트"},
    {"label": "⑤ 공부노트",      "db": "stock_study",    "check": f"[{TODAY}] 개념노트"},
]


async def already_saved(db_key: str, title_contains: str) -> bool:
    """해당 DB에 오늘 제목의 페이지가 이미 있는지 확인"""
    db_id = DB[db_key]
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(f"https://api.notion.com/v1/databases/{db_id}", headers=HEADERS)
        title_prop = next(
            (name for name, p in r.json().get("properties", {}).items() if p.get("type") == "title"),
            "Name"
        )
        r2 = await c.post(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            headers=HEADERS,
            json={"filter": {"property": title_prop, "title": {"contains": title_contains}}}
        )
        return len(r2.json().get("results", [])) > 0


async def claude_summarize(prompt: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        'claude', '-p', prompt,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode('utf-8', errors='replace').strip()


async def fetch_arxiv_paper() -> dict:
    url = (
        "https://export.arxiv.org/api/query"
        "?search_query=cat:cs.AI+AND+cat:cs.LG"
        "&start=0&max_results=1&sortBy=submittedDate&sortOrder=descending"
    )
    async with httpx.AsyncClient() as c:
        r = await c.get(url, follow_redirects=True, timeout=15)
    root = ET.fromstring(r.content)
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    entry = root.find('a:entry', ns)
    return {
        "title":    entry.find('a:title', ns).text.strip().replace('\n', ' '),
        "abstract": entry.find('a:summary', ns).text.strip().replace('\n', ' '),
        "url":      entry.find('a:id', ns).text.strip(),
    }


async def fetch_yna_items(count: int = 5) -> list[dict]:
    async with httpx.AsyncClient() as c:
        r = await c.get("https://www.yna.co.kr/rss/economy.xml", follow_redirects=True, timeout=15)
    root = ET.fromstring(r.content)
    items = root.findall('.//item')
    result = []
    for item in items[:count]:
        desc_elem = item.find('description')
        result.append({
            "title": item.find('title').text or "경제 뉴스",
            "desc":  (desc_elem.text or "")[:300],
            "url":   item.find('link').text or "https://www.yna.co.kr",
        })
    return result


async def main():
    from server import save_summary_to_notion

    print(f"[{TODAY}] 일일 Notion 저장")
    print("=" * 45)

    # 1. 오늘 이미 저장된 항목 확인 (병렬)
    print("저장 여부 확인 중...")
    exist_flags = await asyncio.gather(*[
        already_saved(item["db"], item["check"]) for item in ITEMS
    ])

    skip = dict(zip([item["check"] for item in ITEMS], exist_flags))

    for item, done in zip(ITEMS, exist_flags):
        mark = "이미 저장됨" if done else "저장 필요"
        print(f"  {item['label']:<14} {mark}")

    need = [item for item, done in zip(ITEMS, exist_flags) if not done]
    if not need:
        print()
        print(f"  오늘({TODAY}) 모두 이미 저장되어 있습니다.")
        print("=" * 45)
        return

    # 2. 데이터 수집
    print(f"\n데이터 수집 중...")
    paper, news_items = await asyncio.gather(fetch_arxiv_paper(), fetch_yna_items(5))
    news_text = "\n\n".join(f"[{i+1}] {n['title']}\n{n['desc']}" for i, n in enumerate(news_items))
    print(f"  arxiv: {paper['title'][:50]}...")
    print(f"  연합뉴스: {len(news_items)}건")

    # 3. 필요한 항목만 Claude 요약 생성 (병렬)
    print(f"\nClaude 요약 생성 중 (필요한 {len(need)}개만)...")

    prompts = {
        ITEMS[0]["check"]: f"다음 논문 초록을 한국어로 핵심 기여·방법·성과 순서로 3줄 요약해주세요.\n\n{paper['abstract']}",
        ITEMS[1]["check"]: f"다음 {len(news_items)}개 경제 뉴스를 투자자 관점에서 종합 요약해주세요. 핵심 트렌드, 주요 이슈, 시장 영향 순으로.\n\n{news_text}",
        ITEMS[2]["check"]: f"날짜: {TODAY}\n다음 뉴스를 바탕으로 주간 투자 브리핑을 작성해주세요. 국내 시장 동향, 주요 이슈, 유망 섹터, 투자 전략 포함.\n\n{news_text}",
        ITEMS[3]["check"]: f"다음 뉴스에서 주목할 기업/섹터를 선정해 증권사 리포트 형식으로 작성해주세요. 현황, 투자 포인트, 투자의견, 리스크 포함.\n\n{news_text[:600]}",
        ITEMS[4]["check"]: f"다음 뉴스와 관련된 핵심 투자 개념 1가지를 골라, 개념 정의→실제 사례→투자 적용법 순으로 설명해주세요.\n\n{news_items[0]['title']}\n{news_items[0]['desc']}",
    }

    need_keys = [item["check"] for item in need]
    summaries_list = await asyncio.gather(*[claude_summarize(prompts[k]) for k in need_keys])
    summaries = dict(zip(need_keys, summaries_list))

    # 4. Notion 저장
    print(f"\nNotion 저장 중...")
    saved = 0

    for item in ITEMS:
        key = item["check"]
        if skip[key]:
            print(f"  {item['label']:<14} — 건너뜀")
            continue

        summary = summaries[key]

        if item["label"].startswith("①"):
            result = await save_summary_to_notion(
                title=f"[{TODAY}] {paper['title'][:60]}",
                content=summary, source_url=paper['url'], category="paper",
            )
        elif item["label"].startswith("②"):
            result = await save_summary_to_notion(
                title=f"[{TODAY}] 경제 뉴스 종합", content=summary,
                source_url="https://www.yna.co.kr/economy",
                category="stock_research", sub_category="뉴스",
                source="연합뉴스", tags=["경제"],
            )
        elif item["label"].startswith("③"):
            result = await save_summary_to_notion(
                title=f"[{TODAY}] 주간 투자 브리핑", content=summary,
                source_url="https://www.yna.co.kr/economy",
                category="stock_research", sub_category="주간브리핑",
                source="Claude 자동 수집", tags=["경제"],
            )
        elif item["label"].startswith("④"):
            result = await save_summary_to_notion(
                title=f"[{TODAY}] 섹터 분석 리포트", content=summary,
                source_url="https://www.yna.co.kr/economy",
                category="stock_research", sub_category="증권사리포트",
                source="Claude 자동 분석", tags=["경제"],
            )
        elif item["label"].startswith("⑤"):
            result = await save_summary_to_notion(
                title=f"[{TODAY}] 개념노트: {news_items[0]['title'][:40]}",
                content=summary, source_url=news_items[0]['url'],
                category="stock_study", sub_category="이론",
                difficulty="기초", tags=["경제"],
            )

        ok = "완료" in result
        print(f"  {item['label']:<14} — {'✅ 저장됨' if ok else '❌ 실패'}")
        if ok:
            saved += 1

    print()
    print("=" * 45)
    print(f"  완료: {saved}개 신규 저장")
    print("=" * 45)


asyncio.run(main())
