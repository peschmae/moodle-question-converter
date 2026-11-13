---
type: ddwtos
distractors:
  suffix: [sum, total]
  bound: ['5', '5000']
  function: [absent_over_time, count]
  comparison: [== 0, '> 1']
---

# G2 · Latenz-SLI und fehlendes Target (SW09)

Latenz-SLO: 95 % der Antworten innerhalb von 5 s. Der Python-Client schreibt die Bucket-Grenzen als `0.5`, `1.0`, `5.0`, `10.0`. Vervollständigen Sie die Recording Rule für den Anteil langsamer Antworten und die Regel, die feuert, wenn Prometheus kein gesundes Target für den LLM-Bot hat, egal ob das Target down oder ganz verschwunden ist.

```
- record: service:chatbot_reply_slow:ratio_rate5m
  expr: |
    1 - (
        sum by (service) (rate(chatbot_reply_duration_seconds_[[bucket|suffix]]{le="[[5.0|bound]]"}[5m]))
      / sum by (service) (rate(chatbot_reply_duration_seconds_[[count|suffix]][5m]))
    )

- alert: ChatbotTargetMissing
  expr: [[absent|function]](up{namespace="chatbots", service="chatbots-alan-llm"} [[== 1|comparison]])
  for: 2m
  labels:
    severity: critical
    service: chatbots-alan-llm
```

Ziehen Sie die passenden Begriffe in die Lücken. Nicht alle Begriffe werden gebraucht.

## Solution

Lösung: `bucket`, `5.0`, `count`, `absent`, `== 1`.

`le` muss exakt so geschrieben sein, wie der Client es exportiert: `le="5"` trifft keine Serie, und die Regel bleibt still. Ein Target, das down ist, hat weiterhin `up = 0`; erst `== 1` sorgt dafür, dass «down» und «verschwunden» beide als fehlend gelten.
