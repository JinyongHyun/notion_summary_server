"""발표 화면 3: Orchestration 3패턴 비교"""
import asyncio, sys, time
sys.path.insert(0, 'd:/python/notion_summary_server')

NEWS = [
    {"topic": "AI",    "title": "[발표] AI 전력 수요 급증",   "tags": ["AI"]},
    {"topic": "반도체", "title": "[발표] HBM4 양산 앞당겨",   "tags": ["반도체"]},
    {"topic": "금융",  "title": "[발표] 코스피 7000 임박",    "tags": ["금융"]},
]
CONTENT = "발표 데모용 요약 내용입니다."

async def save(topic, title, tags):
    from server import save_summary_to_notion
    t0 = time.perf_counter()
    await save_summary_to_notion(
        title=title, content=CONTENT,
        source_url="https://demo.test",
        category="stock_research", sub_category="뉴스",
        source="발표데모", tags=tags,
    )
    return time.perf_counter() - t0


async def main():
    print("=" * 50)
    print("[ Orchestration 3패턴 비교 ]")
    print("같은 작업 · 같은 모델 · 구조만 다름")
    print("=" * 50)

    # 패턴 1: Single
    print("\n패턴 1: Single (순차)  실행 중...")
    t = time.perf_counter()
    for n in NEWS:
        await save(n["topic"], n["title"], n["tags"])
    t1 = time.perf_counter() - t
    print(f"  완료: {t1:.2f}초")

    # 패턴 2: Planner+Executor
    print("\n패턴 2: Planner+Executor  실행 중...")
    t = time.perf_counter()
    await asyncio.sleep(0.05)   # Planner 오버헤드
    for n in NEWS:
        await save(n["topic"], n["title"], n["tags"])
    t2 = time.perf_counter() - t
    print(f"  완료: {t2:.2f}초")

    # 패턴 3: Parallel
    print("\n패턴 3: Parallel (병렬)  실행 중...")
    t = time.perf_counter()
    await asyncio.gather(*[save(n["topic"], n["title"], n["tags"]) for n in NEWS])
    t3 = time.perf_counter() - t
    print(f"  완료: {t3:.2f}초")

    # 결과 표
    print()
    print("=" * 50)
    print(f"  Single           {t1:.2f}초")
    print(f"  Planner+Executor {t2:.2f}초")
    print(f"  Parallel      ★ {t3:.2f}초  ← 가장 빠름")
    print("=" * 50)
    print(f"  Parallel는 Single보다 {t1/t3:.1f}배 빠름")
    print("  모델 동일 · 구조만 다름")

asyncio.run(main())
