# memory-bench 에이전트 지침

이 파일이 리포 지침의 실물이다. `CLAUDE.md`는 이 파일을 임포트하는 한 줄이다.
구조·절차·결정은 여기에 옮겨 적지 않고 `README.md`에 둔다.

## 목표
자체 호스팅 메모리 계층(mem0, Hindsight)을 같은 조건에서 비교하는 하네스다. 2026-08에 한 번 재고 닫았다.
두 백엔드를 실제로 돌려 잰 값만 결과로 쓴다.

## 확인 명령
- `uv run --offline --no-project --python 3.13 --with pytest --with-requirements requirements.txt python -m pytest -q tests/`

## README 길잡이
`README.md`는 자동으로 실리지 않는다. 아래 일을 하기 전에 해당 절을 직접 읽는다.
- 벤치를 돌리거나 백엔드를 붙일 때: "Run it"
- 무엇을 재는지 바꿀 때: "What it measures"
- 결과 표를 고칠 때: "Headline result (this run)"
- 어댑터나 폴더를 더할 때: "Layout"

## 규칙
- 단위 시험은 백엔드 없이 돈다. 실제 비교(`bench.run`)는 떠 있는 Hindsight 게이트웨이와 로컬 Ollama가 있어야 하고 CI에서도 돌지 않는다.
- `.venv`에는 pytest가 없다. 시험은 위 확인 명령으로 돌린다(2026-11-13, 9건 통과).
- `COMPARISON.md`는 `python -m bench.report`가 만든다. 손으로 고치지 않는다.
- 결과 표의 값은 `results/`의 백엔드별 JSON에서 온다. 다시 재지 않고 숫자만 바꾸지 않는다.
- 두 백엔드의 LLM 구성은 일부러 다르다(Hindsight는 LLM 없음, mem0는 로컬 Ollama). 같게 맞추려고 한쪽 설정을 바꾸지 않는다.
- 토큰은 환경 변수로만 준다. 값이나 실제 게이트웨이 주소를 코드와 문서에 적지 않는다.
