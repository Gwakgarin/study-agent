# 실행과 배포

## Docker로 실행

```bash
cp .env.example .env
# .env에 OPENAI_API_KEY 입력

docker compose up --build
```

`http://localhost:8000`에서 바로 사용할 수 있습니다. 이미지 빌드 단계에서 React를 빌드하고, FastAPI가 API와 빌드된 화면을 함께 서빙합니다. 노트·FAISS 인덱스·학습 기록(`data/`)은 볼륨으로 연결돼 컨테이너를 다시 만들어도 유지됩니다.

## Fly.io 배포

Docker 이미지를 그대로 배포합니다. SQLite와 FAISS 인덱스가 있는 `/app/data`에 볼륨을 붙여 재배포해도 데이터가 남습니다 (`fly.toml`).

```bash
fly launch --no-deploy --copy-config        # 앱 이름은 fly.toml의 app 값
fly volumes create recap_data --size 1 --region nrt
fly secrets set OPENAI_API_KEY=...
fly deploy
```

## 비용 제한

공개 주소에서 OpenAI 비용이 새지 않도록 여러 단계로 막습니다.

| 설정 | 기본값 | 내용 |
|---|---:|---|
| `CHAT_LIMIT_PER_HOUR` | 30 | 저장된 계정의 시간당 질문 수 |
| `GUEST_CHAT_LIMIT_PER_HOUR` | 10 | 게스트의 시간당 질문 수 |
| `GUEST_LIMIT_PER_IP_PER_DAY` | 5 | 한 IP에서 하루에 만들 수 있는 게스트 수 (쿠키를 지워 새 게스트를 만드는 우회 방지) |
| `GUEST_ENABLED` | true | 끄면 가입한 사람만 사용 |
| `SIGNUP_CODE` | 없음 | 설정하면 이 코드를 아는 사람만 가입·기록 저장 가능 |
| `MAX_UPLOAD_MB`, `MAX_NOTES_PER_PROJECT` | 5, 20 | 업로드 크기와 과목당 노트 수 |

게스트는 노트를 올릴 수 없고, 기록을 저장한 뒤부터 올릴 수 있습니다. 로그인 쿠키는 HttpOnly·SameSite=Lax이고 Fly에서는 HTTPS 전용(`COOKIE_SECURE`)입니다. 이 제한과 별개로 OpenAI 대시보드의 월 사용 한도도 함께 걸어두는 것을 권장합니다.

계정 기능 이전에 만든 과목은 주인이 없어 아무에게도 보이지 않습니다. 가입한 뒤 `python -m src.auth claim <아이디>`로 내 계정에 옮길 수 있습니다 (Fly에서는 `fly ssh console -C "python -m src.auth claim <아이디>"`). 사이트 전체를 비밀번호 하나로 잠그는 `ACCESS_PASSWORD`(HTTP Basic)도 쓸 수 있습니다.

## 노트 색인 (CLI)

```bash
python -m src.ingest <project_id>
```

`data/projects/<project_id>/notes/`에 노트 파일을 넣고 실행하면 FAISS 인덱스가 생성됩니다. 화면이나 API로 올리면 자동으로 색인됩니다. 이미 임베딩한 조각은 캐시(`embeddings.npz`)에서 다시 쓰므로, 노트를 하나 추가하면 그 노트만 새로 임베딩합니다.
