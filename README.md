# rbln-skills

Rebellions RBLN NPU 작업을 위한 Claude Code 스킬 모음입니다.
Claude Code 플러그인 마켓플레이스 형식이라 한 줄로 설치·갱신됩니다.

## 설치

Claude Code에서:

```
/plugin marketplace add rebel-semin/rbln-skills
/plugin install rbln-skills@rbln-skills
```

설치 후 `/rbln-skills:<스킬명>`으로 호출하거나, 관련 작업을 하면 Claude가
알아서 로드합니다. 갱신은 `/plugin marketplace update rbln-skills`.

이 저장소는 private이라 설치하는 쪽에 이 저장소를 읽을 수 있는 git 인증이
있어야 합니다 (`gh auth login` 또는 SSH 키). 인증이 없으면
`marketplace add`가 clone 단계에서 실패합니다.

플러그인 없이 스킬 하나만 쓰려면 심볼릭 링크로도 됩니다.

```bash
git clone https://github.com/rebel-semin/rbln-skills.git
ln -s "$PWD/rbln-skills/skills/rbln-skill-template" ~/.claude/skills/rbln-skill-template
```

## 스킬 목록

| 스킬 | 설명 | 호출 |
|---|---|---|
| `rbln-skill-template` | 이 저장소에 새 스킬을 추가할 때 쓰는 템플릿 겸 체크리스트 | `/rbln-skills:rbln-skill-template` |

새 스킬을 추가하면 이 표에 한 줄 추가합니다.

## 저장소 구조

```
rbln-skills/
├── .claude-plugin/
│   ├── marketplace.json      # 마켓플레이스 카탈로그 (source: "./")
│   └── plugin.json           # 플러그인 매니페스트
├── skills/
│   └── <skill-name>/
│       ├── SKILL.md          # 프론트매터 + 판단 절차 (500줄 이하)
│       ├── references/       # 긴 자료, 필요할 때만 로드됨
│       └── scripts/          # 실행되는 것
├── CONTRIBUTING.md
└── README.md
```

저장소 루트가 곧 플러그인이고 동시에 마켓플레이스입니다. 스킬을 추가할 때
건드릴 곳은 `skills/`와 README 표, 그리고 버전 두 곳뿐입니다.

## 새 스킬 추가

```bash
./skills/rbln-skill-template/scripts/new-skill.sh rbln-compile-debug
```

`skills/rbln-compile-debug/`가 프론트매터까지 채워진 채로 생성됩니다.
작성 규칙은 [CONTRIBUTING.md](CONTRIBUTING.md), 상세 가이드는
[skills/rbln-skill-template/references/authoring-guide.md](skills/rbln-skill-template/references/authoring-guide.md).

## 검증

매니페스트를 고쳤으면 커밋 전에:

```bash
python3 -c "import json;[json.load(open(p)) for p in ['.claude-plugin/marketplace.json','.claude-plugin/plugin.json']];print('ok')"
```
