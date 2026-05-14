"""발표 화면 1-B: MCP 있을 때 - 3가지 카테고리"""
import asyncio, sys, time, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'd:/python/notion_summary_server')

TASKS = [
    {
        "label":    "① AI 논문",
        "title":    "[발표데모] Attention Is All You Need",
        "content":  "Transformer 아키텍처 제안 논문. Self-attention만으로 RNN 없이 seq2seq 구현. BLEU 점수 SOTA 달성.",
        "url":      "https://arxiv.org/abs/1706.03762",
        "category": "paper",
    },
    {
        "label":    "② 주식 리서치",
        "title":    "[발표데모] 삼성전자 HBM3E 공급 확대",
        "content":  "삼성전자 HBM3E 12단 공급 확대 발표. 주요 AI 고객사 3곳과 장기 공급 계약 체결. 연간 HBM 매출 80% 성장 전망.",
        "url":      "https://demo.presentation/news",
        "category": "stock_research",
        "sub_category": "뉴스",
        "tags":     ["반도체", "AI"],
    },
    {
        "label":    "③ 주식 공부노트",
        "title":    "[발표데모] PER (주가수익비율) 개념 정리",
        "content":  "PER = 주가 / EPS. 동종 업종 평균 PER 대비 저평가 여부를 판단하는 지표. 성장주는 높은 PER도 정당화될 수 있음.",
        "url":      "https://demo.presentation/study",
        "category": "stock_study",
        "sub_category": "지표",
        "difficulty": "기초",
        "tags":     ["금융"],
    },
]

async def main():
    from server import save_summary_to_notion

    print("=" * 50)
    print("[ MCP 있을 때: 3가지 카테고리 자동 저장 ]")
    print("=" * 50)

    for task in TASKS:
        print(f"\n{task['label']} 저장 중...")
        t0 = time.perf_counter()
        result = await save_summary_to_notion(
            title=task["title"],
            content=task["content"],
            source_url=task["url"],
            category=task["category"],
            sub_category=task.get("sub_category", ""),
            tags=task.get("tags"),
            difficulty=task.get("difficulty", ""),
        )
        elapsed = time.perf_counter() - t0
        # 결과에서 페이지 URL 줄만 출력
        for line in result.splitlines():
            if "완료" in line or "페이지" in line or "분류" in line:
                print(f"  {line}")
        print(f"  소요: {elapsed:.2f}초")

    print()
    print("=" * 50)
    print("  3개 DB에 자동 라우팅 완료")
    print("  AI 논문 / 주식 리서치 / 주식 공부노트")
    print("=" * 50)

asyncio.run(main())
