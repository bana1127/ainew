# n8n Notification Setup

ClubAgent stores notification rules and calculates targets in the backend. n8n only executes delivery.

## Environment

Set these values in `backend/.env`.

```text
N8N_WEBHOOK_URL=https://your-n8n.example.com/webhook/clubagent-notification
N8N_SECRET=replace-with-shared-secret
N8N_ENABLED=true
FRONTEND_URL=http://localhost:3000
```

## Workflow A: Webhook Immediate Send

1. Create an n8n **Webhook Trigger** with method `POST`.
2. Read the request header `X-ClubAgent-Secret`.
3. Compare it with the secret stored in n8n credentials or environment variables.
4. Stop the workflow with an error response when the secret does not match.
5. Add a **Gmail Send** node.
6. Map fields from `body.payload`:
   - `recipient_email` -> To
   - `subject` -> Subject
   - `body` -> Message
   - `target_url` -> optional link in the message
7. Add an **HTTP Request** node to call ClubAgent:

```http
POST {CLUBAGENT_BACKEND_URL}/api/notifications/log
Content-Type: application/json
```

Example body:

```json
{
  "rule_id": "{{$json.payload.rule_id}}",
  "reminder_type": "{{$json.payload.reminder_type}}",
  "target_type": "{{$json.payload.target_type}}",
  "target_id": "{{$json.payload.target_id}}",
  "recipient_email": "{{$json.payload.recipient_email}}",
  "recipient_name": "{{$json.payload.recipient_name}}",
  "subject": "{{$json.payload.subject}}",
  "body": "{{$json.payload.body}}",
  "target_url": "{{$json.payload.target_url}}",
  "provider": "n8n",
  "provider_message_id": "{{$json.gmailMessageId}}",
  "status": "sent"
}
```

8. Add **Respond to Webhook** with `{ "ok": true }`.

## Workflow B: Schedule Automatic Send

1. Create a **Schedule Trigger**.
2. Add **HTTP Request**:

```http
GET {CLUBAGENT_BACKEND_URL}/api/notifications/due
```

3. Use **Split In Batches** over `items`.
4. Send each item with **Gmail Send**.
5. Call `POST /api/notifications/log` with the result.

## Test

1. Open ClubAgent `/notifications`.
2. Check n8n status.
3. Click Gmail test send.
4. Confirm n8n receives the webhook.
5. Confirm Gmail receives the message.
6. Create a rule and run preview.
7. Click send now.
8. Confirm `notification_delivery_logs` has a `sent` or `failed` row.
