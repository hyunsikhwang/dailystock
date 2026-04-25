# TODO

- [x] 카드에서 반드시 남겨야 할 식별 텍스트를 다시 확인한다.
- [x] 지수 라벨은 복구하고 불필요한 메타는 계속 제거된 상태로 정리한다.
- [x] 검증을 실행하고 결과를 기록한다.

# Review

- 카드 상단에 `KOSPI`, `KOSDAQ` 식별 라벨을 다시 추가했다.
- 상태와 핵심 등락 수치만 유지하고 시간 구간, 현재 지수 같은 메타는 계속 제거했다.
- 검증: `python3 -m py_compile /Users/hyunsikhwang/dailystock/app.py` 통과
- 테스트: 미실행 (사유: `make test`, `npm test`, `pnpm test`, `yarn test`, `pytest -q`에 해당하는 표준 테스트 구성이 저장소에 없음)
