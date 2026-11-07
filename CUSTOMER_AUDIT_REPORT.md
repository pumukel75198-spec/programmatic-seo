# Customer Audit Report

Generated: 2026-11-07 17:30 UTC

## Summary

| Product type | Checked | OK | Auto-healed | Failed |
| --- | ---: | ---: | ---: | ---: |
| APIs | 106 | 103/106 OK | 19 | 3 |
| Alternatives | 113 | 113/113 OK | 0 | 0 |
| Workflows | 86 | 85/86 OK | 1 | 1 |

- `npm run build`: OK
- git commit & push: OK

## Remaining issues

### api:neon-postgres-api
- test_mock.py: does not use the endpoint host 'neon.tech'

### api:planetscale-database-api
- test_mock.py: does not use the endpoint host 'planetscale.com'

### api:sendinblue-sms-api
- api_client.py does not implement the endpoint host 'api.sendinblue.com'

### workflow:postgres-backup-reporting
- workflow kit file 'mock_data.json' is <= 100 bytes

