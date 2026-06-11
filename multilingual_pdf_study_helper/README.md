# 다국어 PDF 지식베이스 학습 도우미 AI

## 1. 프로젝트 소개

외국어 강의자료 PDF를 업로드하면 AI가 PDF 내용을 분석하고, 지식베이스를 참고하여 핵심 개념, 공식, 상세 설명, 복습 문제, 다국어 용어 사전을 정리해주는 로컬 웹앱입니다.

단순 PDF 요약기가 아니라, 중요한 전공 용어를 영어 원어와 한국어/중국어 번역으로 함께 정리하여 원서나 외국어 강의자료 학습을 돕는 것이 특징입니다.

## 2. 이 프로젝트의 차별점

이 프로젝트는 단순히 PDF 내용을 짧게 요약하는 도구가 아니라, 외국어 강의자료를 공부하는 학생을 위한 다국어 학습 도우미입니다.

전공 과목을 외국어 자료로 공부할 때는 내용을 이해하는 것뿐만 아니라 용어를 정확히 익히는 것이 중요합니다. 그래서 이 앱은 중요한 전공 용어를 무조건 번역하지 않고, `Linear Independence(선형독립)`, `Basis(기저)`, `Span(생성공간)`처럼 영어 원어와 한국어/중국어 번역을 함께 정리합니다.

이를 통해 원서나 외국어 강의자료를 공부할 때 필요한 개념 이해와 용어 암기를 동시에 돕습니다.

## 3. 빠른 실행 방법

먼저 터미널에서 `app.py`와 `requirements.txt`가 있는 폴더로 이동합니다.

```bash
cd multilingual_pdf_study_helper
```

그 다음 아래 명령어를 실행합니다.

```bash
pip install -r requirements.txt
streamlit run app.py
```

실행 후 브라우저에서 `http://localhost:8502` 주소로 접속합니다.

만약 아래와 같은 오류가 나오면 현재 터미널 위치가 프로젝트 폴더가 아닌 것입니다.

```text
Could not open requirements file: requirements.txt
File does not exist: app.py
```

이 경우 다시 `cd multilingual_pdf_study_helper`를 실행한 뒤 설치/실행 명령어를 입력하세요.

`streamlit` 명령어가 인식되지 않으면 아래 명령어를 사용해도 됩니다.

```bash
python -m streamlit run app.py
```

## 4. API 키 설정

앱을 처음 실행하면 프로젝트 폴더에 `.env` 파일이 자동으로 만들어집니다.

환경 파일은 두 종류가 있습니다.

```text
.env.example  예시 파일입니다. GitHub에 올려도 됩니다.
.env          실제 API 키를 입력하는 파일입니다. GitHub에 올리지 않습니다.
```

실제로 수정해야 하는 파일은 `.env`입니다.

생성된 `.env` 파일을 열고 아래 값만 수정하면 됩니다.

```text
OPENROUTER_API_KEY=여기에_API_KEY_입력
OPENROUTER_MODEL=사용할_모델명_입력
```

평가 당일 교수님이 제공한 OpenRouter API 키와 모델명을 여기에 입력하면 됩니다.

모델명을 비워두면 기본 무료 모델을 사용합니다.

```text
OPENROUTER_API_KEY=여기에_API_KEY_입력
OPENROUTER_MODEL=
```

`.env` 파일은 `.gitignore`에 포함되어 있어서 GitHub에는 올라가지 않습니다. 실제 API 키는 `.env.example`이 아니라 `.env`에만 입력하면 됩니다.

## 5. 사용 방법

1. PDF 파일을 업로드합니다.
2. 설명 언어를 선택합니다.

   - 한국어
   - 중국어
   - English
   - English + 한국어
   - English + 중국어
   - 한국어 + 중국어
   - English + 한국어 + 중국어

3. 전공 용어 처리 방식을 선택합니다.

   - 영어 원어 유지
   - 영어 + 번역 병기
   - 모두 번역

4. 왼쪽 사이드바의 `OpenRouter 연결 테스트` 버튼으로 API 연결 상태를 확인합니다.
5. `분석 시작` 버튼을 누릅니다.
6. 분석 결과를 확인합니다.

## 6. 주요 기능

- PDF 텍스트 자동 추출
- 이미지 기반 스캔 PDF OCR 보조 추출
- PDF 페이지/문단 단위 출처 지식베이스 자동 생성
- 출처 지식베이스 검색 및 Markdown/JSON 다운로드
- 지식베이스 기반 관련 개념 검색
- OpenRouter API 기반 AI 분석
- 주요 개념, 공식, 핵심 내용 정리
- 다국어 용어 사전 생성
- 복습 문제 생성
- OpenRouter 연결 테스트 기능

## 7. 자주 발생하는 문제

### API 키 오류가 나는 경우

`.env` 파일이 있는지 확인하고, `OPENROUTER_API_KEY` 값이 제대로 입력되어 있는지 확인하세요.

### PDF 텍스트를 추출할 수 없는 경우

이미지 기반 스캔본 PDF일 수 있습니다. 현재 버전은 OCR을 시도합니다. OCR이 작동하지 않으면 `PyMuPDF`, `pytesseract`, `Pillow`, 그리고 Tesseract OCR 프로그램 설치 여부를 확인하세요.

### AI 분석이 실패하는 경우

OpenRouter API 키, 모델명, 인터넷 연결 상태를 확인해주세요. 웹페이지의 연결 테스트 버튼을 먼저 눌러보는 것을 권장합니다.

## 8. 제한사항

- 이미지 기반 스캔 PDF는 OCR 품질에 따라 인식률이 달라질 수 있습니다.
- PDF가 너무 길면 일부 내용만 분석될 수 있습니다.
- AI 응답은 사용하는 모델에 따라 달라질 수 있습니다.
- AI 분석 기능은 OpenRouter API 호출을 위해 인터넷 연결이 필요합니다.

<details>
<summary>파일 구조 자세히 보기</summary>

```text
app.py                 Streamlit 웹페이지 실행 파일
analyzer.py            PDF 분석 전체 흐름 연결
pdf_extractor.py       PDF 텍스트 추출
ai_client.py           OpenRouter API 호출
knowledge_base.py      지식베이스 검색
safe_utils.py          안전한 값 변환과 예외처리 보조 함수
data/                  샘플 지식베이스 저장 폴더
requirements.txt       필요한 라이브러리 목록
.env.example           환경변수 예시 파일
.env                   실제 API 키 입력 파일, GitHub에는 올리지 않음
```

</details>

<details>
<summary>지식베이스 교체 방법</summary>

웹앱은 `knowledge_base.py`의 `search_knowledge_base(query_text, top_k=5)` 함수를 사용합니다.
팀원이 만든 지식베이스를 연결하려면 이 함수가 아래와 같은 리스트를 반환하도록 맞추면 됩니다.

```python
[
    {
        "title": "Linear Independence",
        "keywords": ["linear independence", "선형독립", "线性无关"],
        "content": "Linear Independence는 벡터들이 서로 종속되지 않는 성질입니다."
    }
]
```

</details>
