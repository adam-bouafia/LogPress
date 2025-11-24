# Ground Truth Annotations

This directory contains manually verified annotations for accuracy evaluation.

## Structure

```
ground_truth/
├── apache/
│   ├── ground_truth_template.json    (example format)
│   └── apache_ground_truth.json      (100 verified annotations)
├── healthapp/
│   └── healthapp_ground_truth.json
├── zookeeper/
│   └── zookeeper_ground_truth.json
├── openstack/
│   └── openstack_ground_truth.json
└── proxifier/
    └── proxifier_ground_truth.json
```

## Annotation Format

```json
{
  "dataset": "Apache",
  "total_logs": 100,
  "logs": [
    {
      "id": 1,
      "raw": "[Thu Jun 09 06:07:04 2005] [notice] LDAP: Built with OpenLDAP",
      "fields": [
        {
          "type": "TIMESTAMP",
          "value": "Thu Jun 09 06:07:04 2005",
          "start": 1,
          "end": 25,
          "confidence": 1.0
        },
        {
          "type": "SEVERITY",
          "value": "notice",
          "start": 28,
          "end": 34,
          "confidence": 1.0
        },
        {
          "type": "MESSAGE",
          "value": "LDAP: Built with OpenLDAP",
          "start": 36,
          "end": 61,
          "confidence": 1.0
        }
      ],
      "verified": true
    }
  ]
}
```

## Semantic Types

- `TIMESTAMP` - Date/time values
- `SEVERITY` - Log levels (info, error, warning, etc.)
- `IP_ADDRESS` - IPv4/IPv6 addresses
- `PROCESS_ID` - Process/thread IDs
- `FUNCTION_CALL` - Function/method names
- `MODULE` - Module/component names
- `USER_ID` - User identifiers
- `STATUS_CODE` - HTTP/system status codes
- `ERROR_CODE` - Error codes
- `METRIC` - Numerical metrics
- `MESSAGE` - Free-text messages

## Creating Annotations

1. Generate templates:
   ```bash
   python bin/comparison/generate_ground_truth.py --dataset Apache --count 100
   ```

2. Review generated `*_draft.json` files

3. Correct any misclassifications

4. Verify field boundaries

5. Set `verified: true` for each log

6. Rename to remove `_draft` suffix

## Quality Guidelines

- Focus on accuracy over quantity
- 80-100 high-quality annotations per dataset
- Skip ambiguous or malformed logs
- Document any uncertainties in notes
- Cross-validate with team members if possible
