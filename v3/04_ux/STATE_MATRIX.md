# UI State Matrix

所有可交互核心能力至少检查：
- initial / no data
- loading <500ms
- long-running stage
- empty
- partial data
- success
- error recoverable
- error terminal
- offline
- reconnecting
- permission denied
- auth expired
- model unavailable
- tool unavailable
- awaiting clarification
- proposal pending confirmation
- executing
- awaiting user
- conflict/version changed
- unknown outcome
- cancelled
- deleted/revoked

要求：用户永远知道“现在发生什么”和“能做什么”。
