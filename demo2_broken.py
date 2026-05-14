"""발표 화면 2: 망가진 MCP"""
import asyncio, sys, time
sys.path.insert(0, 'd:/python/notion_summary_server')

async def main():
    print("=" * 50)
    print("[ 망가진 MCP — 결함 3개 주입 ]")
    print("=" * 50)
    print()
    print("결함 1: 잘못된 DB ID  (00000...32자리)")
    print("결함 2: tool description 없음")
    print("결함 3: timeout = 0.001초")
    print()
    print("실행 중...")

    from server_broken import save_summary_to_notion
    t0 = time.perf_counter()
    result = await save_summary_to_notion(
        title="망가진 MCP 테스트",
        content="이 저장은 실패해야 합니다.",
        source_url="https://broken.test",
        category="stock_research",
    )
    elapsed = time.perf_counter() - t0

    print(result)
    print()
    print(f"소요 시간: {elapsed:.2f}초")
    print()
    print("→ 모델은 그대로. Harness만 바뀜.")
    print("→ 실패 레이어: Layer 3 (Harness)")

asyncio.run(main())
