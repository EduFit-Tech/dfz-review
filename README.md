# 디지털 핏 존 개발 리뷰

디지털 핏 존 팀이 만들고 고치는 것을 외부 리뷰어가 보고 의견을 보내는 페이지입니다.

- 페이지: https://edufit-tech.github.io/dfz-review/
- 이 저장소는 **공개**입니다. 리뷰어에게 필요한 글과 그림만 둡니다.
  코드, 파일 경로, 브랜치, 커밋, 서버 구성, 보안 세부는 싣지 않습니다.

## 구성

| 경로 | 무엇 |
|---|---|
| `index.html` | 개발 항목 목록 (만들어지는 파일) |
| `games/` | 게임 체험판 페이지와 그림 |
| `data/changes.json` | 개발 항목의 원본 — 리뷰어용 요약 |
| `data/games.json` | 게임 페이지의 원본 — 설명과 바뀐 기록 |
| `tools/build_review.py` | 위 두 자료로 페이지를 다시 만든다 |

## 고치는 법

1. `data/changes.json`에 항목을 더하거나 고친다.
2. `python -I tools/build_review.py`
3. 올리기 전에 내부 정보가 없는지 확인한다.

의견 받기는 `data/games.json`의 `requestUrl`에 받을 주소를 적으면 켜집니다. 비어 있으면 「준비 중」으로 표시됩니다.

체험판 페이지와 생성 도구의 바탕은 HRYoon0/dfz 의 `review/`입니다.
