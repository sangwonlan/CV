# 자소서 프롬프트 생성기

Streamlit 기반 자소서 프롬프트 생성기입니다. 포트폴리오를 저장하고, 회사/직무/질문에 맞는 자소서 작성용 프롬프트를 생성합니다.

## 현재 구조

- 앱 엔트리포인트: `app.py`
- 데이터 저장: SQLite
- 사용자 분리: 계정별 개별 SQLite 파일
- 사용자 계정 저장소: `data/users.db`
- 사용자별 포트폴리오 저장소: `data/<user>_<hash>.db`

## 로컬 실행

1. Python 가상환경 생성
2. 의존성 설치
3. Streamlit 실행

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## 다른 사람이 접속하게 배포하는 방법

### 1. 가장 빠른 공유: Streamlit Community Cloud

적합한 경우:
- 일단 URL 하나로 보여주고 싶을 때
- 데모/테스트 용도
- 무료 배포가 필요할 때

절차:
1. 이 폴더를 GitHub 저장소로 올립니다.
2. Streamlit Community Cloud에서 저장소를 연결합니다.
3. Main file path를 `app.py`로 지정합니다.
4. Deploy를 누릅니다.

중요한 제한:
- 이 앱은 SQLite 파일을 로컬 디스크에 저장합니다.
- Streamlit Community Cloud에서는 파일이 재배포/재시작 시 유지되지 않을 수 있습니다.
- 즉, 회원 정보나 포트폴리오가 영구 저장되어야 하는 서비스에는 권장되지 않습니다.

### 2. 실제 운영에 더 적합: Render 또는 Railway

적합한 경우:
- 사용자 데이터가 유지되어야 할 때
- 로그인 기반으로 계속 써야 할 때

권장 방식:
- 앱은 그대로 두고, 데이터 폴더만 영구 디스크에 마운트합니다.
- 환경변수 `PORTFOLIO_DATA_DIR` 를 영구 디스크 경로로 지정합니다.

예시:
- Render persistent disk 경로: `/var/data/portfolio`
- 환경변수: `PORTFOLIO_DATA_DIR=/var/data/portfolio`

실행 커맨드 예시:

```bash
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

## 배포 전 체크

- `data/*.db` 파일은 저장소에 올리지 않는 것이 좋습니다.
- `.gitignore`에 SQLite 파일 제외 규칙을 추가했습니다.
- 현재 비밀번호는 공개 배포를 고려해 PBKDF2 기반 해시로 저장됩니다.
- 예전에 만든 계정이 있다면 기존 SHA-256 해시도 로그인 시 호환됩니다.

## 권장 배포 선택

- 무료 데모 공유: Streamlit Community Cloud
- 실제 사용자 저장이 필요한 공개 서비스: Render + Persistent Disk

## 현재 확인 가능한 로컬 체크

- 자동 테스트: 없음
- 린트/타입체크 설정: 없음

현재 폴더에는 `requirements.txt` 외의 테스트/배포 자동화 설정 파일이 없습니다.

## GitHub에 올리는 순서

1. 새 GitHub 저장소를 만듭니다.
2. 이 폴더에서 아래 순서로 커밋합니다.

```powershell
git init
git add .
git status
git commit -m "Initial deployable Streamlit app"
```

3. `data/*.db`, `portfolio.db`, `.venv/` 가 `git status`에 안 잡히는지 확인합니다.
4. GitHub 원격 저장소를 연결하고 push 합니다.

```powershell
git remote add origin <YOUR_GITHUB_REPO_URL>
git branch -M main
git push -u origin main
```

## Render에서 바로 배포하는 순서

이 저장소에는 `render.yaml` 이 포함되어 있습니다.

1. GitHub에 push 합니다.
2. Render Dashboard에서 `New > Blueprint` 를 선택합니다.
3. 이 저장소를 연결합니다.
4. `render.yaml` 내용을 확인하고 Apply 합니다.
5. 서비스가 생성되면 URL이 발급됩니다.
6. 발급된 URL을 다른 사람에게 공유하면 됩니다.

현재 `render.yaml` 기본값:
- 서비스 이름: `jaso-portfolio-app`
- 지역: `singapore`
- 플랜: `starter`
- 저장 경로: `/var/data/portfolio`

참고:
- Persistent Disk는 Render 문서 기준으로 유료 web service에서 사용 가능합니다.
- 비용 없이 데모만 빠르게 열고 싶으면 Streamlit Community Cloud를 쓰고, 저장 유지가 필요하면 Render를 쓰는 편이 낫습니다.
