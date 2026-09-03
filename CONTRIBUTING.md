# 기여 규칙

## 스킬 하나의 조건

스킬은 **반복되는 판단 절차**를 담습니다. 한 번 쓰고 마는 명령어 모음이나
단순 사실은 스킬이 아니라 CLAUDE.md나 사내 위키에 두는 편이 맞습니다.

스킬로 만들 가치가 있는지 판단하는 기준:

- 같은 지시를 세 번 이상 붙여넣은 적이 있다.
- 절차에 분기가 있다(증상에 따라 조치가 갈린다).
- 틀리면 손해가 크고, 맞는 절차가 문서로 흩어져 있다.

## 디렉터리와 이름

```
skills/<skill-name>/SKILL.md
```

- `<skill-name>`은 kebab-case, `SKILL.md`의 `name` 필드와 같아야 합니다.
- 이름은 사용자가 타이핑할 명령어입니다. `rbln-compile-debug`처럼 무엇에 관한
  것인지 드러나야 하고, `helper`, `utils` 같은 이름은 쓰지 않습니다.
- `rbln-` 접두사는 선택입니다. 플러그인 접두사(`/rbln-skills:`)가 이미 붙습니다.

## SKILL.md 작성

필수는 `name`과 `description` 둘뿐입니다.

`description`은 Claude가 이 스킬을 로드할지 결정할 때 읽는 **유일한** 문장입니다.
무엇을 하는지 먼저 쓰고, 언제 쓰는지를 이어 붙이되 트리거를 문자 그대로
넣으세요 — 도구 이름, 정확한 에러 문자열, 파일 확장자, 디바이스 세대.

본문은 판단 절차로 씁니다. 최소한 다음이 있어야 합니다.

- 적용 조건 (지금 이 상황이 맞는지 한눈에)
- 절차와 분기
- **완료 조건** — 이게 없으면 Claude가 멈출 시점을 모릅니다

500줄이 넘어가면 `references/`로 밀어냅니다. `SKILL.md`는 스킬이 걸릴 때마다
통째로 읽히지만 `references/`는 필요할 때만 읽힙니다.

부가 필드(`disable-model-invocation`, `allowed-tools`, `paths` 등)는 필요할 때만
씁니다. 판단 기준은
[authoring-guide.md](skills/rbln-skill-template/references/authoring-guide.md)에 있습니다.

## 공개 저장소 주의

퍼블릭 저장소입니다. 다음은 넣지 않습니다.

- 사내 호스트명, 사내 IP, 토큰·키
- 고객사명, 계약 정보
- 미공개 제품/실리콘 코드명, 미공개 벤치마크 수치

필요하면 `<HOST>`, `<CUSTOMER>` 같은 자리표시자를 씁니다.

## 검증한 것만 쓴다

본문에 적은 명령은 실제 RBLN 호스트에서 실행해 본 것이어야 합니다. 확인하지
못한 절차는 넣지 말고, 넣어야 한다면 미검증임을 명시하세요.
버전에 의존하는 내용은 드라이버·`rebel-compiler`·SDK 버전과 디바이스 세대를
함께 적습니다.

## PR 체크리스트

- [ ] 디렉터리명 = `name` 필드 = 의도한 명령어
- [ ] `description`에 구체적인 트리거(도구명·에러 문자열)가 하나 이상
- [ ] 본문에 완료 조건이 있음
- [ ] 긴 자료는 `references/`로 분리
- [ ] 명령을 실제로 실행해 확인
- [ ] 비밀정보 없음
- [ ] README 스킬 표에 추가
- [ ] `.claude-plugin/plugin.json`과 `marketplace.json`의 `version` 갱신
- [ ] JSON 파싱 통과 (`README.md`의 검증 명령)

## 버전

`plugin.json`과 `marketplace.json`의 `version`을 같이 올립니다. 스킬 추가·
동작 변경은 minor, 문구 수정은 patch.
