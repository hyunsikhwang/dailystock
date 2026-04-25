# TODO

- [x] 디버그 패널의 현재 렌더 위치를 확인한다.
- [x] 디버그 패널을 주요 카드와 차트 뒤, 화면 최하단으로 이동한다.
- [x] 검증을 실행하고 결과를 기록한다.

# Review

- 야간선물/변동성 디버그 패널 호출을 차트 렌더 이후로 이동했다.
- 주요 카드와 차트가 먼저 보이고 디버그 정보는 화면 최하단에 나오도록 순서를 정리했다.
- 검증: `python3 -m py_compile /Users/hyunsikhwang/dailystock/app.py` 통과
- 테스트: 미실행 (사유: `make test`, `npm test`, `pnpm test`, `yarn test`, `pytest -q`에 해당하는 표준 테스트 구성이 저장소에 없음)
