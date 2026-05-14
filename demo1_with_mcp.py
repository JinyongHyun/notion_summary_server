"""발표 화면 1-B: MCP 있을 때 — 실시간 수집 → Claude 요약 → Notion 자동 저장"""
import asyncio, sys, time, io, httpx, xml.etree.ElementTree as ET
from datetime import datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'd:/python/notion_summary_server')

TODAY = datetime.now().strftime("%Y-%m-%d")


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


async def fetch_yna_news(idx: int = 0) -> dict:
    async with httpx.AsyncClient() as c:
        r = await c.get("https://www.yna.co.kr/rss/economy.xml", follow_redirects=True, timeout=15)
    root = ET.fromstring(r.content)
    items = root.findall('.//item')
    item = items[idx]
    desc_elem = item.find('description')
    return {
        "title": item.find('title').text or "경제 뉴스",
        "desc":  (desc_elem.text or "")[:400],
        "url":   item.find('link').text or "https://www.yna.co.kr",
    }


async def main():
    from server import save_summary_to_notion

    print("=" * 50)
    print("[ MCP 있을 때: 실시간 수집 + Claude 요약 + Notion 저장 ]")
    print(f"  실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # ① AI 논문 (arxiv 최신)
    print("\n① AI 논문 수집 중 (arxiv cs.AI)...")
    paper = await fetch_arxiv_paper()
    print(f"  제목: {paper['title'][:65]}...")
    print("  요약 중 (Claude)...")
    paper_summary = await claude_summarize(
        f"다음 논문 초록을 한국어로 3줄 요약해주세요. 핵심 기여·방법·성과 순서로.\n\n{paper['abstract']}"
    )
    t0 = time.perf_counter()
    result = await save_summary_to_notion(
        title=f"[{TODAY}] {paper['title'][:60]}",
        content=paper_summary,
        source_url=paper['url'],
        category="paper",
    )
    elapsed = time.perf_counter() - t0
    for line in result.splitlines():
        if "완료" in line or "페이지" in line or "분류" in line:
            print(f"  {line}")
    print(f"  소요: {elapsed:.2f}초")

    # ② 주식 리서치 (연합뉴스 경제 최신)
    print("\n② 주식 리서치 수집 중 (연합뉴스 경제)...")
    news0 = await fetch_yna_news(0)
    print(f"  제목: {news0['title'][:65]}")
    print("  요약 중 (Claude)...")
    research_summary = await claude_summarize(
        f"투자자 관점에서 핵심 요약 → 시장 영향 → 투자 시사점 순으로 3줄 요약해주세요.\n\n"
        f"제목: {news0['title']}\n내용: {news0['desc']}"
    )
    t0 = time.perf_counter()
    result = await save_summary_to_notion(
        title=f"[{TODAY}] {news0['title'][:60]}",
        content=research_summary,
        source_url=news0['url'],
        category="stock_research",
        sub_category="뉴스",
        tags=["경제"],
    )
    elapsed = time.perf_counter() - t0
    for line in result.splitlines():
        if "완료" in line or "페이지" in line or "분류" in line:
            print(f"  {line}")
    print(f"  소요: {elapsed:.2f}초")

    # ③ 주식 공부노트 (뉴스 키워드 → 투자 개념 설명)
    print("\n③ 주식 공부노트 (뉴스 키워드 → 투자 개념 설명)...")
    news1 = await fetch_yna_news(1)
    print(f"  키워드 뉴스: {news1['title'][:65]}")
    print("  개념 도출 중 (Claude)...")
    concept = await claude_summarize(
        f"다음 뉴스와 관련된 핵심 투자 개념 1가지를 골라, "
        f"개념 정의 → 실제 사례 → 투자 적용법 순으로 초보자도 이해하게 설명해주세요.\n\n"
        f"뉴스: {news1['title']}\n{news1['desc']}"
    )
    t0 = time.perf_counter()
    result = await save_summary_to_notion(
        title=f"[{TODAY}] 개념노트: {news1['title'][:45]}",
        content=concept,
        source_url=news1['url'],
        category="stock_study",
        sub_category="이론",
        difficulty="기초",
        tags=["경제"],
    )
    elapsed = time.perf_counter() - t0
    for line in result.splitlines():
        if "완료" in line or "페이지" in line or "분류" in line:
            print(f"  {line}")
    print(f"  소요: {elapsed:.2f}초")

    print()
    print("=" * 50)
    print("  실시간 수집 → Claude 요약 → 3개 DB 자동 라우팅 완료")
    print("  arxiv 논문 / 연합뉴스 경제 / 투자 개념 노트")
    print("=" * 50)


asyncio.run(main())
