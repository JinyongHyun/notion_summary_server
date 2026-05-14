"""
실험 03: Orchestration 3패턴 비교
과제: "AI, 반도체, 금융 뉴스를 각각 요약해서 Notion에 저장하기 (3건)"

패턴 1 - Single Agent    : 순차적으로 하나씩 처리
패턴 2 - Planner+Executor: Planner가 작업 목록 생성 → Executor가 순차 실행
패턴 3 - Parallel        : 3개 작업을 asyncio.gather로 동시 실행
"""
import asyncio
import time

# 측정 항목 저장소
results = {}

# ─────────────────────────────────────────────
# 공통: Notion 저장 함수 (실제 server.py 재사용)
# ─────────────────────────────────────────────
async def save_one(topic: str, title: str, content: str, tags: list[str]) -> dict:
    """단일 뉴스 저장 + 소요 시간 측정"""
    from server import save_summary_to_notion
    t0 = time.perf_counter()
    result = await save_summary_to_notion(
        title=title,
        content=content,
        source_url=f"https://experiment.test/{topic}",
        category="stock_research",
        sub_category="뉴스",
        source="실험03",
        tags=tags,
    )
    elapsed = time.perf_counter() - t0
    ok = "200" in result or "완료" in result
    return {"topic": topic, "elapsed": elapsed, "ok": ok, "result": result[:80]}


NEWS = [
    {
        "topic": "AI",
        "title": "[실험03] AI 데이터센터 전력 수요 급증",
        "content": "글로벌 AI 데이터센터 전력 수요가 2026년 상반기 기준 전년 대비 120% 증가했다. "
                   "주요 빅테크 기업들은 원자력 및 재생에너지 확보 경쟁에 나서고 있으며, "
                   "국내 전력 인프라 기업들의 수주 기회도 확대될 전망이다.",
        "tags": ["AI", "국내"],
    },
    {
        "topic": "반도체",
        "title": "[실험03] HBM4 양산 일정 앞당겨",
        "content": "SK하이닉스와 삼성전자가 HBM4 양산 일정을 당초 계획보다 6개월 앞당기기로 했다. "
                   "엔비디아 Blackwell Ultra 플랫폼 탑재를 위한 조기 공급 요청에 따른 것으로, "
                   "HBM 시장 점유율 경쟁이 더욱 치열해질 전망이다.",
        "tags": ["반도체", "AI"],
    },
    {
        "topic": "금융",
        "title": "[실험03] 코스피 7000 돌파 임박, 증권사 수혜",
        "content": "코스피가 6,900p를 돌파하며 7,000p 고지가 가시권에 들어왔다. "
                   "거래대금이 역대 최대 수준인 30조원을 기록하면서 증권사 순이익이 급증하고 있다. "
                   "삼성증권, 키움증권 등 대형 증권사들의 2분기 실적 기대치가 대폭 상향됐다.",
        "tags": ["금융", "국내"],
    },
]


# ─────────────────────────────────────────────
# 패턴 1: Single Agent (순차)
# ─────────────────────────────────────────────
async def pattern_single() -> dict:
    print("\n[패턴 1: Single] 순차 실행 시작...")
    t_total = time.perf_counter()
    items = []
    for n in NEWS:
        r = await save_one(n["topic"], n["title"], n["content"], n["tags"])
        items.append(r)
        print(f"  {n['topic']}: {r['elapsed']:.2f}s  ok={r['ok']}")
    elapsed = time.perf_counter() - t_total
    return {"pattern": "Single", "total_elapsed": elapsed, "items": items,
            "token_estimate": 3 * 850, "failure_layer": "없음 (순차라 앞 실패 시 중단)"}


# ─────────────────────────────────────────────
# 패턴 2: Planner + Executor (순차이지만 계획 단계 분리)
# ─────────────────────────────────────────────
async def planner() -> list[dict]:
    """Planner: 작업 목록을 구조화된 형태로 반환 (LLM 역할 시뮬레이션)"""
    await asyncio.sleep(0.05)  # Planner의 thinking 오버헤드 시뮬레이션
    plan = [
        {"id": 1, "topic": n["topic"], "title": n["title"],
         "content": n["content"], "tags": n["tags"]} for n in NEWS
    ]
    print("  [Planner] 작업 계획 생성 완료:", [p["topic"] for p in plan])
    return plan


async def executor(plan: list[dict]) -> list[dict]:
    """Executor: Planner 결과를 받아 순차 실행"""
    items = []
    for task in plan:
        r = await save_one(task["topic"], task["title"], task["content"], task["tags"])
        items.append(r)
        print(f"  [Executor] {task['topic']}: {r['elapsed']:.2f}s  ok={r['ok']}")
    return items


async def pattern_planner_executor() -> dict:
    print("\n[패턴 2: Planner+Executor] 실행 시작...")
    t_total = time.perf_counter()
    plan = await planner()
    items = await executor(plan)
    elapsed = time.perf_counter() - t_total
    return {"pattern": "Planner+Executor", "total_elapsed": elapsed, "items": items,
            "token_estimate": 3 * 850 + 120,  # Planner 오버헤드 +120 토큰
            "failure_layer": "Planner 실패 시 전체 중단 / Executor 단계별 격리 가능"}


# ─────────────────────────────────────────────
# 패턴 3: Parallel Sub-Agent (동시 실행)
# ─────────────────────────────────────────────
async def pattern_parallel() -> dict:
    print("\n[패턴 3: Parallel] 병렬 실행 시작...")
    t_total = time.perf_counter()
    tasks = [
        save_one(n["topic"], n["title"], n["content"], n["tags"])
        for n in NEWS
    ]
    items = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.perf_counter() - t_total
    for item in items:
        if isinstance(item, Exception):
            print(f"  ERROR: {item}")
        else:
            print(f"  {item['topic']}: {item['elapsed']:.2f}s  ok={item['ok']}")
    return {"pattern": "Parallel", "total_elapsed": elapsed,
            "items": [i for i in items if not isinstance(i, Exception)],
            "token_estimate": 3 * 850,  # 동시 실행이라 총 토큰은 동일
            "failure_layer": "개별 sub-agent 독립 실패 → 나머지 계속 진행"}


# ─────────────────────────────────────────────
# 실행 및 결과 출력
# ─────────────────────────────────────────────
async def main():
    print("=" * 60)
    print("실험 03: Orchestration 3패턴 비교")
    print("=" * 60)

    r1 = await pattern_single()
    r2 = await pattern_planner_executor()
    r3 = await pattern_parallel()

    print("\n" + "=" * 60)
    print("결과 요약")
    print("=" * 60)
    print(f"{'패턴':<22} {'총 소요시간':>12} {'추정 토큰':>10} {'성공 건수':>8}")
    print("-" * 60)
    for r in [r1, r2, r3]:
        ok_count = sum(1 for i in r["items"] if i.get("ok"))
        print(f"{r['pattern']:<22} {r['total_elapsed']:>10.2f}s {r['token_estimate']:>10} {ok_count:>8}/3")

    print("\n실패 격리 전략:")
    for r in [r1, r2, r3]:
        print(f"  {r['pattern']}: {r['failure_layer']}")

    # 결과를 파일로 저장
    import json
    with open("d:/python/notion_summary_server/experiment_results.json", "w", encoding="utf-8") as f:
        json.dump({"single": r1, "planner_executor": r2, "parallel": r3}, f, ensure_ascii=False, indent=2)
    print("\n결과 저장: experiment_results.json")


if __name__ == "__main__":
    asyncio.run(main())
