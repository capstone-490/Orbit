# Priority Actions

Shows the signed-in advisor's urgent follow-ups on the dashboard, with optional AI suggestions.

## Prioritization criteria

Only **Pending** or **In Progress** follow-ups for the advisor's own clients are considered.

A follow-up is urgent if it is:

| Category        | Rule                                    |
|-----------------|-----------------------------------------|
| Overdue         | Due date is before today                |
| Due soon        | Due today or within the next 2 days     |
| High priority   | Priority is High and due within 7 days  |

Sorted by: category (overdue, due soon, high priority), then priority (High, Medium, Low), then earliest due date.

## API

- `GET /priority-actions?limit=5`: urgent follow-ups, most urgent first.
- `GET /priority-actions/suggestions`: AI suggestions, with `status` set to `available`, `unavailable` or `disabled`.

## AI suggestions

- Off by default. Enable with `AI_SUGGESTIONS_ENABLED=true`, `AI_BASE_URL` and `AI_MODEL`.
- Only the follow-up reason, stage, priority and urgency are sent; never client names or contact details.
- If AI fails, the dashboard still works and shows "unavailable".
