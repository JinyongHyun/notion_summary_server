"""발표 화면 1-A: MCP 없을 때 — 실시간 뉴스를 텍스트로만 출력"""
import sys, io, httpx, xml.etree.ElementTree as ET
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def fetch_latest_news() -> dict:
    try:
        r = httpx.get("https://www.yna.co.kr/rss/economy.xml", timeout=10, follow_redirects=True)
        root = ET.fromstring(r.content)
        item = root.findall('.//item')[0]
        title = item.find('title').text or "경제 뉴스"
        desc_elem = item.find('description')
        desc = desc_elem.text if desc_elem is not None and desc_elem.text else title
        link = item.find('link').text or "https://www.yna.co.kr/economy"
        return {"title": title, "desc": desc[:200], "url": link}
    except Exception:
        return {"title": "오늘의 경제 뉴스", "desc": "뉴스를 불러올 수 없습니다.", "url": "https://www.yna.co.kr"}

news = fetch_latest_news()

print("=" * 50)
print("[ MCP 없을 때 ]")
print("=" * 50)
print()
print(f"질문: 오늘 경제 뉴스 요약해줘")
print()
print("Claude 답변:")
print(f"  {news['title']}")
print(f"  {news['desc']}")
print(f"  출처: {news['url']}")
print()
print("→ 텍스트만 출력됨. Notion 저장 없음.")
print("→ 창 닫으면 사라짐. 수동 복사 필요.")
