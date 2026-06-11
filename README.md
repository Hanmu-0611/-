# 다국어 PDF 지식베이스 학습 도우미 AI

외국어 강의자료 PDF를 업로드하면 PDF 텍스트를 추출하고, 샘플 지식베이스를 참고해 주요 개념, 공식/정의, 시험 핵심 내용, 상세 설명, 복습 문제, 다국어 용어 사전을 정리하는 Streamlit 앱입니다.

API 키가 없어도 앱 실행, PDF 업로드, PDF 텍스트 추출, 출처 지식베이스 생성, 로컬 분석 기능은 사용할 수 있습니다. OpenRouter 기반 AI 분석과 연결 테스트를 사용하려면 `.env` 파일에 실제 API 키를 입력해야 합니다.

## 실행 방법

최종 앱은 `multilingual_pdf_study_helper` 폴더 안에 있습니다.
터미널을 열고 아래 명령어를 입력합니다.

```bash
cd multilingual_pdf_study_helper
pip install -r requirements.txt
streamlit run app.py --server.port 8502
```

실행 후 브라우저에서 아래 주소로 접속합니다.

```text
http://localhost:8502
```

`streamlit` 명령어가 인식되지 않으면 아래처럼 실행해도 됩니다.

```bash
python -m streamlit run app.py --server.port 8502
```

api key가 입력이 잘 되었더라도 OpenRouter 연결 테스트에서 처음 몇번은 실패했다고 뜰 수 있습니다.

## API 키 설정

`.env.example`을 참고해 프로젝트 폴더 안에 `.env` 파일을 만들고 값을 입력합니다.

```text
OPENROUTER_API_KEY=여기에_API_KEY_입력
OPENROUTER_MODEL=qwen/qwen3-next-80b-a3b-instruct:free
OLLAMA_MODEL=qwen2.5:7b
```

API 키가 없으면 `OPENROUTER_API_KEY=`처럼 비워두면 됩니다. 이 경우 OpenRouter 연결 테스트와 OpenRouter AI 분석은 실패 메시지를 보여주지만, 로컬 PDF 분석 기능은 계속 사용할 수 있습니다.

## UI 언어

앱 상단에서 사이트 언어를 선택할 수 있습니다.

- 한국어
- English
- 中文

설명 언어 선택에서도 각 언어 이름은 가능한 한 해당 언어로 표시됩니다. 예를 들어 중국어는 `中文`, 영어는 `English`로 표시됩니다.

## 지식베이스 샘플

`multilingual_pdf_study_helper/data/knowledge_base_sample.json`은 앱이 PDF 내용과 비교할 기본 샘플 지식베이스입니다. `knowledge_base.py`가 이 파일을 읽어서 PDF와 관련 있는 항목을 자동 검색합니다.

직접 만든 지식베이스로 바꾸고 싶다면 같은 JSON 구조로 항목을 수정하면 됩니다.

## 주요 파일

```text
multilingual_pdf_study_helper/
  app.py                 Streamlit 앱
  analyzer.py            PDF 분석 흐름
  ai_client.py           OpenRouter/Ollama 호출
  pdf_extractor.py       PDF 텍스트 추출
  knowledge_base.py      지식베이스 검색
  data/knowledge_base_sample.json
  .env.example           환경변수 예시
```

## 주의(개발자용)

`.env`에는 실제 API 키가 들어갈 수 있으므로 커밋하지 않습니다. 제출 전에는 `git status`에서 `.env`, `streamlit.log`, `streamlit.err.log`가 커밋 대상에 들어가지 않는지 확인하세요.
