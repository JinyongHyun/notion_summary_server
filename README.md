# notion_summary_server

AI 논문 요약, 주식 리서치, 공부노트, 주간 브리핑을 Notion 데이터베이스에 자동 저장하는 MCP 서버.

> ⚠️ **Notion 관련 작업(논문 저장, 주식 리서치, 주간 브리핑)은 이 폴더를 VS Code에서 열고 사용해야 합니다.**
> `CLAUDE.md`가 이 폴더에 위치해 있어, 여기서 열어야 Claude가 Notion 규칙을 적용합니다.

---

## 📁 파일 구조

```
notion_summary_server/
├── CLAUDE.md           # Claude Code 작업 규칙 (Notion MCP + 주식 리서치)
├── server.py           # MCP 서버 메인 파일
├── .env                # 환경변수 (직접 생성, git 제외)
├── .env.example        # 환경변수 템플릿
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🗄️ Notion DB 구조

모두 **"Finance & 투자"** 페이지 (`33117b872be68187a1b4ddc51261856e`) 내 인라인 DB.

| DB | ID | 용도 |
|---|---|---|
| 📰 주식 리서치 | `39bf50a1aca04ad2a10079e958cf96d4` | 뉴스 / 산업분석 / 증권사리포트 / 주간브리핑 |
| 📚 주식 공부노트 | `d1afcb876857487eb978c1a8e0952d05` | 용어 / 이론 / 지표 / 전략 / 산업지식 |
| 📖 AI 논문 | `34617b872be68060a474e18a73510f38` | 논문 리뷰 및 요약 |

---

## 🔧 도구 (Tool)

| 도구 | 설명 |
|---|---|
| `save_summary_to_notion` | 논문·주식 리서치·공부노트를 Notion DB에 새 페이지로 저장 |
| `update_notion_page` | 기존 Notion 페이지에 내용 추가(append) |

### `save_summary_to_notion` 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `title` | string | ✅ | 페이지 제목 |
| `content` | string | ✅ | 본문 내용 |
| `source_url` | string | ✅ | 원본 URL |
| `category` | `"paper"` \| `"stock_research"` \| `"stock_study"` | ✅ | 저장 DB 선택 |
| `sub_category` | string | ❌ | 카테고리 세분류 (아래 참고) |
| `source` | string | ❌ | 출처 (예: "한국경제", "삼성증권") |
| `tags` | list[string] | ❌ | 태그 목록 (예: `["반도체", "AI", "국내"]`) |
| `difficulty` | string | ❌ | 난이도 — `stock_study` 전용 (`"기초"` \| `"중급"` \| `"고급"`) |

#### sub_category 옵션

| category | sub_category 선택지 |
|---|---|
| `stock_research` | `뉴스` \| `산업분석` \| `증권사리포트` \| `주간브리핑` |
| `stock_study` | `용어` \| `이론` \| `지표` \| `전략` \| `산업지식` |
| `paper` | 해당 없음 |

### `update_notion_page` 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `page_id` | string | ✅ | Notion 페이지 ID 또는 URL |
| `content` | string | ✅ | 추가할 내용 |
| `section_title` | string | ❌ | 섹션 제목 (입력 시 `━━━ 제목 ━━━` 형식으로 구분선 표시) |

---

## ⚙️ 설치

```bash
cd d:\python\notion_summary_server

# 가상환경 생성 (선택)
python -m venv .venv
.venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

---

## 🔑 환경변수 설정

`.env.example`을 복사해 `.env` 파일 생성:

```bash
copy .env.example .env
```

`.env` 파일 내용:

```env
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# AI 논문 DB
NOTION_PAPER_DB_ID=34617b872be68060a474e18a73510f38

# 주식 리서치 DB (뉴스 / 산업분석 / 증권사리포트 / 주간브리핑)
NOTION_STOCK_RESEARCH_DB_ID=39bf50a1aca04ad2a10079e958cf96d4

# 주식 공부노트 DB (용어 / 이론 / 지표 / 전략 / 산업지식)
NOTION_STOCK_STUDY_DB_ID=d1afcb876857487eb978c1a8e0952d05
```

---

## 🔌 Claude Code MCP 등록

터미널에서 실행:

```bash
claude mcp add notion_summary_server -- python d:/python/notion_summary_server/server.py
```

또는 `~/.claude/settings.json`에 직접 추가:

```json
{
  "mcpServers": {
    "notion_summary_server": {
      "command": "python",
      "args": ["d:/python/notion_summary_server/server.py"]
    }
  }
}
```

등록 후 Claude Code 재시작 → `/mcp` 명령으로 연결 확인.

---

## 💬 사용 예시

Claude에게 자연어로 요청하면 자동으로 MCP 도구를 선택해 실행합니다.

```
이 논문 정리해줘: https://arxiv.org/abs/2310.06825
```
→ `category="paper"` 로 AI 논문 DB에 저장

```
삼성전자 관련 한국경제 기사 저장해줘: https://www.hankyung.com/...
```
→ `category="stock_research"`, `sub_category="뉴스"`, `tags=["반도체", "국내"]`

```
PER 개념 정리해줘
```
→ `category="stock_study"`, `sub_category="지표"`, `difficulty="기초"`

```
주간 브리핑 해줘
```
→ WebSearch(거시경제/미국/국내/섹터) → 종합 분석 → `sub_category="주간브리핑"` 으로 저장

---

## 📋 주간 브리핑 수집 항목

| 항목 | 내용 |
|---|---|
| 🌐 글로벌 거시경제 | 연준 금리, 달러인덱스, WTI 유가, 금 가격 |
| 🇺🇸 미국 시장 | S&P500 / 나스닥 등락, QQQ·SPY·SOXX ETF |
| 🇰🇷 국내 시장 | KOSPI / KOSDAQ, 외국인·기관 수급 |
| 📊 유망 섹터 | 모멘텀 상위 2~3개 섹터, 이유 설명 |
| 💡 ETF 추천 | 섹터별 대표 ETF + 투자 근거 + 리스크 |

---

## ✍️ 콘텐츠 포맷 규칙

- 마크다운 헤더(`##`, `###`) 사용 금지 → `━━━ 섹션명 ━━━` 형식 사용
- 이모지 적극 활용 (섹션 구분, 수치 강조, 추천/주의 표시)
- 문단 형식으로 충분히 서술 (bullet 나열 금지)
- 뉴스/리포트: 핵심 요약 → 시장 영향 → 투자 시사점 순
- 공부노트: 개념 정의 → 실제 사례 → 투자 적용법 순

---

## ⚠️ 주의사항

- API 키는 절대 git에 커밋하지 마세요. `.env`는 `.gitignore`에 포함되어 있습니다.
- Notion DB의 title 프로퍼티 이름은 자동으로 감지합니다.
- 본문이 길면 자동 분할 저장합니다 (Notion 블록 제한: 2000자).
- MCP 서버 코드 변경 후에는 Claude Code를 재시작해야 새 스키마가 반영됩니다.
