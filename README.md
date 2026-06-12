# 다국어 PDF 지식베이스 학습 도우미 AI

외국어 강의자료 PDF를 업로드하면 PDF 텍스트를 추출하고, 샘플 지식베이스를 참고해 주요 개념, 공식/정의, 시험 핵심 내용, 상세 설명, 복습 문제, 다국어 용어 사전을 정리하는 Streamlit 앱입니다.

API 키가 없어도 앱 실행, PDF 업로드, PDF 텍스트 추출, 출처 지식베이스 생성, 로컬 분석 기능은 사용할 수 있습니다. OpenRouter 기반 AI 분석과 연결 테스트를 사용하려면 `.env` 파일에 실제 API 키를 입력해야 합니다.

## 免费模式和手动输入 API

这个程序可以用两种方式运行。

### 1. 免费模式，不需要 API Key

如果没有 API Key，可以在网页左侧选择下面这个模式。

```text
로컬 분석만 사용 (API Key 없음)
```

免费模式可以使用这些功能。

```text
PDF 文本提取
PDF 出处知识库生成
自动搜索知识库
手动搜索知识库
Markdown / JSON 下载
中文对照整理提示
```

这种模式不会调用在线 AI，所以不需要付费，也不需要输入 Key。

### 2. 在网页内部手动输入 API Key

如果要使用 OpenRouter 在线 AI，可以直接在网页左侧输入，不需要手动改代码。

```text
AI 模式选择：
OpenRouter 온라인 AI 사용

打开：
API Key / 모델 설정

输入：
OpenRouter API Key
OpenRouter 모델

点击：
API 설정 저장
```

可以使用的免费模型示例：

```text
qwen/qwen3-next-80b-a3b-instruct:free
```

如果老师或平台提供了其他模型名，也可以手动填入 `OpenRouter 모델` 输入框。

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

웹앱을 종료하려면 ctrl+c를 입력하면 종료할 수 있습니다.
## API 키 설정

`.env.example`을 참고해 프로젝트 폴더 안에 `.env` 파일을 만들고 값을 입력합니다.

```text
OPENROUTER_API_KEY=여기에_API_KEY_입력
OPENROUTER_MODEL=여기에_모델명_입력
OLLAMA_MODEL=qwen2.5:7b
```

API 키가 없으면 `OPENROUTER_API_KEY=`처럼 비워두면 됩니다. 이 경우 OpenRouter 연결 테스트와 OpenRouter AI 분석은 실패 메시지를 보여주지만, 로컬 PDF 분석 기능은 계속 사용할 수 있습니다.

## 网页内部 API 输入代码

网页左侧 API 输入框代码在 `multilingual_pdf_study_helper/app.py` 的 `show_ai_settings_sidebar()` 函数中。

```python
with st.sidebar.expander("API Key / 모델 설정"):
    api_key_input = st.text_input(
        "OpenRouter API Key",
        type="password",
        placeholder="sk-or-...",
    )
    model_input = st.text_input(
        "OpenRouter 모델",
        value=model_name,
    )
    if st.button("API 설정 저장"):
        key_to_save = api_key_input.strip() or current_key
        if save_openrouter_settings(key_to_save, model_input):
            st.sidebar.success("저장했습니다. 다시 분석을 실행해주세요.")
```

保存 API Key 的代码在 `save_openrouter_settings()` 函数中。它会把网页里输入的 Key 和模型名保存到本地 `.env` 文件。

```python
def save_openrouter_settings(api_key: str, model_name: str) -> bool:
    normalized_key = normalize_openrouter_api_key(api_key)

    ENV_FILE.write_text(
        "\n".join(
            [
                f"OPENROUTER_API_KEY={normalized_key}",
                f"OPENROUTER_MODEL={model_name}",
                "OLLAMA_MODEL=qwen2.5:7b",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return True
```

也就是说，用户可以在网页内部手动输入 API Key，不需要打开 `.env` 文件。

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
2명이서 작업했기에 내용이 조금 부실할 수 있습니다..
