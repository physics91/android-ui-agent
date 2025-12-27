# Android UI Agent MCP Server

AI 에이전트가 Android 화면을 직접 "볼 수 있게" 해주는 최소 MCP 서버

## 설계 철학

- **MCP 서버** = "눈" (화면 데이터 전달)
- **AI 에이전트** = "두뇌" (분석, 판단, 수정 모두 담당)

MCP는 오직 **화면 데이터를 AI에게 직접 전달**하는 역할만 수행합니다.

## 도구 (2개만!)

| Tool | 설명 | 반환값 |
|------|------|--------|
| `capture_screenshot` | 스크린샷 캡처 | base64 PNG 이미지 |
| `dump_ui_hierarchy` | UI 계층 구조 추출 | XML 문자열 |

## 설치

```bash
cd /home/physics91/dev/android-tester
pip install -e .
```

## Claude Code 설정

`~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "android-ui-agent": {
      "command": "python",
      "args": ["/home/physics91/dev/android-tester/src/server.py"]
    }
  }
}
```

## 사용 예시

Claude Code에서 자연어로 요청:

```
"연결된 안드로이드 디바이스의 스크린샷을 캡처하고 UI 문제를 분석해줘"
```

AI 에이전트가:
1. `capture_screenshot()` → base64 이미지 반환
2. AI Vision으로 직접 분석 → "버튼이 너무 작습니다"
3. `dump_ui_hierarchy()` → XML 반환
4. AI가 XML에서 요소 정보 파악 → "btn_submit의 bounds=[100,200][136,232]"

## 의존성

- `mcp>=1.0.0` - MCP 서버 프레임워크
- `uiautomator2>=3.4.0` - Android UI 자동화
- `Pillow>=10.0.0` - 이미지 처리

## 테스트

```bash
# Android 디바이스 연결 필요
pytest tests/test_server.py -v
```
