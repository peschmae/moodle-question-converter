---
type: ddwtos
distractors:
  keyword: [expr, keep_firing_for]
  function: [irate, deriv]
  label: [pod, le]
  threshold: ['0.99', '0.144']
  operator: [or, unless]
  severity: [warning]
---

# G1 · Recording Rule und Fast-Burn-Alert (SW09)

Das Verfügbarkeits-SLO des Chatbots lautet: 99 % der Nachrichten werden über 30 Tage ohne Fehler beantwortet. Vervollständigen Sie die Recording Rule für die 30-Minuten-Fehlerquote pro Service und den Fast-Burn-Alert, der aufbietet, wenn das Budget 14,4-mal zu schnell verbraucht wird. Die 5-Minuten-Recording-Rule existiert bereits.

```
groups:
  - name: chatbots-slo
    rules:
      - [[record|keyword]]: service:chatbot_messages_errors:ratio_rate30m
        expr: |
            sum by ([[service|label]]) ([[rate|function]](chatbot_messages_total{status="error"}[30m]))
          / sum by (service) (rate(chatbot_messages_total[30m]))

      - [[alert|keyword]]: ChatbotErrorBudgetFastBurn
        expr: |
              service:chatbot_messages_errors:ratio_rate30m > (14.4 * [[0.01|threshold]])
          [[and|operator]] service:chatbot_messages_errors:ratio_rate5m  > (14.4 * 0.01)
        [[for|keyword]]: 2m
        labels:
          severity: [[critical|severity]]
```

Ziehen Sie die passenden Begriffe in die Lücken. Nicht alle Begriffe werden gebraucht.

## Solution

Lösung: `record`, `service`, `rate`, `alert`, `0.01`, `and`, `for`, `critical`.

Die Schwelle ist Burn Rate × (1 − SLO) = 14,4 × 0,01. Beide Fenster müssen gleichzeitig überschritten sein (`and`): das lange für die Signifikanz, das kurze, damit der Alert nach dem Fix schnell auflöst. `irate` gehört nicht in Regeln, und alarmiert wird auf den Service, nicht auf den Pod.
