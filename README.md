# 함께 쓰기 · Coders Agent 데모

[데모 열기](https://core-v2.coders.kr/use/gh-e2ac3f0106c86b75e4fbfeabde) · [Coders 활동 규약](https://dev.coders.kr/activity.html)

브라우저와 CLI가 같은 PostgreSQL 문서를 조회·수정합니다.
저장이 완료되면 Core 활동을 발행하고, 열린 브라우저가 데이터를 재조회해 해당 문서를 강조합니다.

앱의 데이터는 워크스페이스 PostgreSQL에 저장되고, 저장 완료 후 Coders 활동으로 화면에 변경을 알립니다.
브라우저와 CLI는 `state`와 `save`라는 동일한 앱 API를 사용합니다.
Coders가 `DATABASE_URL`과 `CODERS_URL`을 실행 환경에 제공합니다.

## Agent 연결

1. 데모를 열고 Coders 로그인 후 워크스페이스를 생성합니다.
2. Coders 칩에서 **Agent 연결 → 연결 링크 만들기 → 링크 복사**를 선택합니다.
3. Agent에게 링크를 전달합니다. Agent는 지침을 읽어 연결을 요청하고 사용자에게 승인 링크와 확인 코드를 보여줍니다.
4. 사용자가 승인하면 같은 워크스페이스에 접속합니다. 연결 기간은 기본 **24시간**, **1시간·24시간·7일** 중 선택합니다.

이 저장소의 연결 도우미를 직접 실행할 수도 있습니다.

```bash
git clone https://github.com/cykim8811/coders-activity-demo
cd coders-activity-demo
python3 connect.py 'Coders 칩에서 복사한 링크' --name '내 Agent'
```

승인 후 도우미가 출력한 인증 파일 경로를 CLI에 전달합니다. 키는 터미널에 출력하지 않습니다.

```bash
python3 agent.py --connection /path/to/connection.json state
python3 agent.py --connection /path/to/connection.json watch
python3 agent.py --connection /path/to/connection.json save 'Agent가 바꾼 제목'
```

Python 표준 라이브러리만 사용합니다. Agent도 이 명령이나 같은 HTTP API를 사용할 수 있습니다.
인증 파일에는 승인된 앱의 고정된 커밋 주소와 워크스페이스가 포함됩니다.
Coders의 Agent 연결 화면에서 연결을 해제할 수 있습니다.

## 확인할 수 있는 것

- 브라우저가 저장하면 CLI에서 변경된 문서를 조회할 수 있습니다.
- CLI가 저장하면 브라우저가 문서를 재조회하고 저장 영역을 강조합니다.
- 두 브라우저를 같은 워크스페이스로 열어도 동일하게 동작합니다.
- 서로 다른 워크스페이스는 별도 DB·활동 구독·공동 계좌를 사용합니다.

화면은 같은 데이터를 사용하는 앱 UI이고, CLI는 그 데이터의 JSON 표현을 받습니다.
`actor_label=Agent`는 앱이 표시하는 이름이며 독립적으로 인증된 Agent 신원을 의미하지 않습니다.
워크스페이스 생성·보관·실행에는 Coders의 일반 요금이 적용됩니다.

## 재시도

`save`는 `action_id`로 DB 변경을 멱등 처리합니다. 응답이 불명확하면 같은 행동 ID와 요청 ID로 결과를 확인합니다.
`saved=true, activity_pending=true`이면 DB 저장이 완료되고 알림 발행이 남아 있습니다.
같은 행동 ID·입력에 새로운 `--request-id`를 지정하면 저장을 유지한 채 알림을 재시도합니다.
각 HTTP 호출에는 기존 Coders 요금이 적용됩니다.
