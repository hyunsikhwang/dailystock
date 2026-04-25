# TODO

- [x] 현재 카드에서 제거할 불필요한 텍스트를 확인한다.
- [x] 상태와 핵심 등락 수치만 남기는 형태로 카드 텍스트를 정리한다.
- [x] 검증을 실행하고 결과를 기록한다.

# Review

- 카드 내부에서 라벨, 시간 구간, 현재 지수 텍스트를 제거했다.
- 상태와 핵심 등락 수치만 한 줄에 남겨 정보량을 최소화했다.
- 검증: `python3 -m py_compile /Users/hyunsikhwang/dailystock/app.py` 통과
- 테스트: 미실행 (사유: `make test`, `npm test`, `pnpm test`, `yarn test`, `pytest -q`에 해당하는 표준 테스트 구성이 저장소에 없음)
