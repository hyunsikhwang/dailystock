# TODO

- [x] 현재 추세 카드에서 세로 공간을 차지하는 구조를 다시 확인한다.
- [x] 더 작고 더 미니멀한 배지형 카드로 재구성한다.
- [x] 검증을 실행하고 결과를 기록한다.

# Review

- 카드 패딩과 그림자를 한 단계 더 줄이고 보조 장식을 제거해 배지형 밀도로 압축했다.
- 상태, 변동값, 등락률을 두 줄 안에 정리하고 하단 메타도 더 짧게 줄였다.
- 검증: `python3 -m py_compile /Users/hyunsikhwang/dailystock/app.py` 통과
- 테스트: 미실행 (사유: `make test`, `npm test`, `pnpm test`, `yarn test`, `pytest -q`에 해당하는 표준 테스트 구성이 저장소에 없음)
