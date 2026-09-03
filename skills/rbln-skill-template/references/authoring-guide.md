# rbln-skills 작성 가이드 (상세)

`SKILL.md` 본문에서 링크로만 참조하는 문서입니다. 필요할 때만 읽히므로
길어도 비용이 들지 않습니다.

## description 쓰는 법

Claude가 스킬을 로드할지 결정할 때 읽는 것은 `description` 한 줄뿐입니다.
본문은 그 결정 이후에 읽힙니다. 그래서 트리거를 문자 그대로 적어야 합니다.

나쁜 예:

```yaml
description: RBLN 컴파일을 도와줍니다.
```

"도와준다"에 걸리는 사용자 발화는 없습니다.

좋은 예:

```yaml
description: >-
  rebel-compiler로 PyTorch 모델을 .rbln로 컴파일할 때의 실패를 진단합니다.
  torch.compile 백엔드 오류, "unsupported op" 메시지, RBLN_COMPILE_* 환경변수,
  compile_*.py 스크립트를 다룰 때 사용합니다.
```

규칙 세 가지:

1. **무엇을 하는지 먼저, 언제 쓰는지 그다음.** 목록 앞쪽이 매칭에 더 크게 기여합니다.
2. **고유명사를 넣는다.** 도구 이름(`rebel-compiler`, `vllm-rbln`, `rbln-stat`),
   에러 문자열, 파일 확장자(`.rbln`), 디바이스 이름(`ATOM`, `ATOM+`, `REBEL`).
3. **description + when_to_use 합쳐 1,536자에서 잘린다.** 핵심 트리거를 앞에 둡니다.

## 본문 구조

스킬 본문은 주제 설명이 아니라 **판단 절차**입니다. 다음 형태를 유지하세요.

```markdown
## 증상 확인
<무엇을 실행해서 무엇을 보는가>

## 분기
- A가 보이면 → <조치>
- B가 보이면 → references/b.md 를 읽고 <조치>

## 완료 조건
<무엇이 참이면 끝난 것인가>
```

"완료 조건"이 없는 스킬은 Claude가 언제 멈춰야 할지 모릅니다. 반드시 넣으세요.

## 파일 배치 기준

| 넣는 곳 | 기준 |
|---|---|
| `SKILL.md` | 매번 필요한 판단 절차. 500줄 이하. |
| `references/*.md` | 버전별 표, 에러 코드 목록, 긴 배경 설명. 조건부로만 읽힘. |
| `scripts/*` | 실행되는 것. 본문에 명령을 늘어놓지 말고 스크립트를 호출하게 한다. |
| `assets/` | 템플릿 파일, 설정 예시 등 그대로 복사되는 산출물. |

`scripts/`를 참조할 때는 절대경로가 아니라 `${CLAUDE_SKILL_DIR}`을 씁니다.
플러그인으로 설치되면 스킬은 저장소가 아니라 플러그인 캐시에 놓입니다.

```markdown
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/collect.sh *)
```

본문과 `allowed-tools`에 같은 경로를 쓰면 권한 프롬프트 없이 실행됩니다.

## RBLN 도메인 규칙

- **숫자를 남긴다.** "느려진다"가 아니라 "TPOT 41ms → 96ms". 재현 조건
  (배치 크기, 시퀀스 길이, 디바이스 수)을 함께 적습니다.
- **버전을 고정한다.** 드라이버 버전, `rebel-compiler` 버전, SDK 릴리스를
  명시하고 `references/`에 둡니다. 본문에 박아두면 갱신을 놓칩니다.
- **디바이스 세대를 구분한다.** ATOM과 ATOM+에서 같은 플래그가 반대로 동작하는
  경우가 있습니다. 세대를 쓰지 않은 조언은 쓰지 않은 것만 못합니다.
- **공개 저장소다.** 내부 호스트명, 사내 IP, 토큰, 고객사명, 미공개 제품
  코드명을 넣지 않습니다. 필요하면 `<HOST>` 같은 자리표시자를 씁니다.

## 로컬에서 시험하기

플러그인을 설치하지 않고 이 저장소의 스킬만 바로 쓰려면 심볼릭 링크를 겁니다.

```bash
ln -s "$PWD/skills/rbln-compile-debug" ~/.claude/skills/rbln-compile-debug
```

Claude Code를 다시 시작하면 `/rbln-compile-debug`로 잡힙니다. 편집한 내용은
다음 세션에 반영됩니다.

## 참고

- 스킬 프론트매터 전체 레퍼런스: <https://code.claude.com/docs/en/skills>
- 플러그인·마켓플레이스: <https://code.claude.com/docs/en/plugin-marketplaces>
- Agent Skills 표준: <https://agentskills.io>
