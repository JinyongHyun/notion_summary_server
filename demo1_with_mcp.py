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


def news_block(items: list[dict]) -> str:
    return "\n\n".join(f"[{i+1}] {n['title']}\n{n['desc']}" for i, n in enumerate(items))


async def main():
    from server import save_summary_to_notion

    print("=" * 55)
    print("[ MCP 있을 때: 실시간 수집 + Claude 요약 + Notion 저장 ]")
    print(f"  실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    # ━━ 사전 수집 ━━
    print("\n데이터 수집 중...")
    paper, news_items = await asyncio.gather(fetch_arxiv_paper(), fetch_yna_items(5))
    news_text = news_block(news_items)
    print(f"  arxiv: {paper['title'][:55]}...")
    print(f"  연합뉴스 경제 {len(news_items)}건 수집 완료")

    # ① AI 논문
    print("\n① AI 논문 — Claude 요약 중...")
    paper_summary = await claude_summarize(
        f"다음 논문 초록을 한국어로 핵심 기여·방법·성과 순서로 3줄 요약해주세요.\n\n{paper['abstract']}"
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

    # ② 뉴스 종합 — 여러 뉴스를 하나의 페이지로
    print(f"\n② 뉴스 종합 ({len(news_items)}건 → 1페이지) — Claude 요약 중...")
    combined = await claude_summarize(
        f"다음 {len(news_items)}개 경제 뉴스를 투자자 관점에서 종합해 하나의 요약 리포트로 작성해주세요. "
        f"핵심 트렌드, 주요 이슈, 시장 영향 순으로 서술해주세요.\n\n{news_text}"
    )
    t0 = time.perf_counter()
    result = await save_summary_to_notion(
        title=f"[{TODAY}] 경제 뉴스 종합",
        content=combined,
        source_url="https://www.yna.co.kr/economy",
        category="stock_research",
        sub_category="뉴스",
        source="연합뉴스",
        tags=["경제", "종합"],
    )
    elapsed = time.perf_counter() - t0
    for line in result.splitlines():
        if "완료" in line or "페이지" in line or "분류" in line:
            print(f"  {line}")
    print(f"  소요: {elapsed:.2f}초")

    # ③ 주간브리핑
    print(f"\n③ 주간브리핑 — Claude 생성 중...")
    briefing = await claude_summarize(
        f"날짜: {TODAY}\n\n다음 경제 뉴스를 바탕으로 주간 투자 브리핑을 작성해주세요. "
        f"국내 시장 동향, 주요 이슈, 유망 섹터, 투자 전략 포함.\n\n{news_text}"
    )
    t0 = time.perf_counter()
    result = await save_summary_to_notion(
        title=f"[{TODAY}] 주간 투자 브리핑",
        content=briefing,
        source_url="https://www.yna.co.kr/economy",
        category="stock_research",
        sub_category="주간브리핑",
        source="Claude 자동 수집",
        tags=["경제", "주간브리핑"],
    )
    elapsed = time.perf_counter() - t0
    for line in result.splitlines():
        if "완료" in line or "페이지" in line or "분류" in line:
            print(f"  {line}")
    print(f"  소요: {elapsed:.2f}초")

    # ④ 증권사리포트
    print(f"\n④ 증권사리포트 — Claude 생성 중...")
    report = await claude_summarize(
        f"다음 뉴스 중 가장 주목할 만한 기업 또는 섹터를 선정해 증권사 분석 리포트 형식으로 작성해주세요. "
        f"기업/섹터 현황, 투자 포인트, 투자의견, 리스크 요인 포함.\n\n{news_text[:800]}"
    )
    t0 = time.perf_counter()
    result = await save_summary_to_notion(
        title=f"[{TODAY}] 섹터 분석 리포트",
        content=report,
        source_url="https://www.yna.co.kr/economy",
        category="stock_research",
        sub_category="증권사리포트",
        source="Claude 자동 분석",
        tags=["경제"],
    )
    elapsed = time.perf_counter() - t0
    for line in result.splitlines():
        if "완료" in line or "페이지" in line or "분류" in line:
            print(f"  {line}")
    print(f"  소요: {elapsed:.2f}초")

    # ⑤ 주식 공부노트
    print(f"\n⑤ 주식 공부노트 — 뉴스 키워드에서 개념 도출 중...")
    concept = await claude_summarize(
        f"다음 뉴스와 관련된 핵심 투자 개념 1가지를 골라, "
        f"개념 정의 → 실제 사례 → 투자 적용법 순으로 초보자도 이해하게 설명해주세요.\n\n"
        f"뉴스: {news_items[0]['title']}\n{news_items[0]['desc']}"
    )
    t0 = time.perf_counter()
    result = await save_summary_to_notion(
        title=f"[{TODAY}] 개념노트: {news_items[0]['title'][:40]}",
        content=concept,
        source_url=news_items[0]['url'],
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
    print("=" * 55)
    print("  실시간 수집 → Claude 요약 → 자동 라우팅 완료")
    print("  AI 논문 | 뉴스 종합 | 주간브리핑 | 증권사리포트 | 공부노트")
    print("=" * 55)


asyncio.run(main())
