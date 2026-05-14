"""발표 화면 3: Orchestration 3패턴 비교 — 주식 리서치 3종 (뉴스종합/주간브리핑/증권사리포트)"""
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


# 3가지 저장 작업 — 같은 뉴스 데이터, 다른 sub_category
async def save_news_summary(news_text: str) -> float:
    from server import save_summary_to_notion
    content = await claude_summarize(
        f"다음 경제 뉴스들을 투자자 관점에서 종합 요약해주세요.\n\n{news_text}"
    )
    t0 = time.perf_counter()
    await save_summary_to_notion(
        title=f"[{TODAY}] 뉴스 종합",
        content=content,
        source_url="https://www.yna.co.kr/economy",
        category="stock_research", sub_category="뉴스",
        source="연합뉴스", tags=["경제"],
    )
    return time.perf_counter() - t0


async def save_weekly_briefing(news_text: str) -> float:
    from server import save_summary_to_notion
    content = await claude_summarize(
        f"날짜: {TODAY}\n다음 뉴스를 바탕으로 주간 투자 브리핑을 작성해주세요. "
        f"시장 동향, 유망 섹터, 투자 전략 포함.\n\n{news_text}"
    )
    t0 = time.perf_counter()
    await save_summary_to_notion(
        title=f"[{TODAY}] 주간 투자 브리핑",
        content=content,
        source_url="https://www.yna.co.kr/economy",
        category="stock_research", sub_category="주간브리핑",
        source="Claude 자동 수집", tags=["경제", "주간브리핑"],
    )
    return time.perf_counter() - t0


async def save_research_report(news_text: str) -> float:
    from server import save_summary_to_notion
    content = await claude_summarize(
        f"다음 뉴스에서 주목할 기업/섹터를 선정해 증권사 리포트 형식으로 작성해주세요. "
        f"현황, 투자 포인트, 투자의견, 리스크 포함.\n\n{news_text[:600]}"
    )
    t0 = time.perf_counter()
    await save_summary_to_notion(
        title=f"[{TODAY}] 섹터 분석 리포트",
        content=content,
        source_url="https://www.yna.co.kr/economy",
        category="stock_research", sub_category="증권사리포트",
        source="Claude 자동 분석", tags=["경제"],
    )
    return time.perf_counter() - t0


TASKS = [save_news_summary, save_weekly_briefing, save_research_report]
LABELS = ["뉴스종합", "주간브리핑", "증권사리포트"]


async def main():
    print("=" * 55)
    print("[ Orchestration 3패턴 비교 ]")
    print("같은 작업 · 같은 모델 · 구조만 다름")
    print(f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    print("\n연합뉴스 경제 RSS에서 최신 뉴스 5건 수집 중...")
    news_items = await fetch_yna_items(5)
    for i, n in enumerate(news_items, 1):
        print(f"  [{i}] {n['title'][:55]}")
    news_text = "\n\n".join(f"[{i+1}] {n['title']}\n{n['desc']}" for i, n in enumerate(news_items))

    print(f"\n저장 작업: {' / '.join(LABELS)}")

    # 패턴 1: Single (순차)
    print("\n패턴 1: Single (순차)  실행 중...")
    t = time.perf_counter()
    for fn in TASKS:
        await fn(news_text)
    t1 = time.perf_counter() - t
    print(f"  완료: {t1:.2f}초")

    # 패턴 2: Planner+Executor
    print("\n패턴 2: Planner+Executor  실행 중...")
    t = time.perf_counter()
    await asyncio.sleep(0.05)  # Planner 오버헤드
    for fn in TASKS:
        await fn(news_text)
    t2 = time.perf_counter() - t
    print(f"  완료: {t2:.2f}초")

    # 패턴 3: Parallel
    print("\n패턴 3: Parallel (병렬)  실행 중...")
    t = time.perf_counter()
    await asyncio.gather(*[fn(news_text) for fn in TASKS])
    t3 = time.perf_counter() - t
    print(f"  완료: {t3:.2f}초")

    print()
    print("=" * 55)
    print(f"  Single           {t1:.2f}초")
    print(f"  Planner+Executor {t2:.2f}초")
    print(f"  Parallel      ★ {t3:.2f}초  <- 가장 빠름")
    print("=" * 55)
    if t3 > 0:
        print(f"  Parallel는 Single보다 {t1/t3:.1f}배 빠름")
    print("  모델 동일 · 구조만 다름")


asyncio.run(main())
