# WAFR Question Library Configuration

This directory contains curated Well-Architected Framework Review questions optimized for document-based assessment.

## Purpose

The question library serves as a fallback when AWS Well-Architected Tool API is unavailable, ensuring assessments can continue with high-quality, curated questions.

## Structure

Questions are organized by pillar:
- `security_questions.json` - Security pillar questions
- `reliability_questions.json` - Reliability pillar questions
- `performance_questions.json` - Performance Efficiency pillar questions
- `cost_optimization_questions.json` - Cost Optimization pillar questions
- `operational_excellence_questions.json` - Operational Excellence pillar questions
- `sustainability_questions.json` - Sustainability pillar questions

## Question Format

Each question file contains an array of question objects:

```json
{
  "questions": [
    {
      "id": "SEC-01",
      "text": "How does the architecture implement data encryption at rest and in transit?",
      "capabilities": ["encryption"],
      "services": ["KMS", "S3", "RDS", "DynamoDB"],
      "criteria": {
        "required_capabilities": ["encryption"],
        "best_practices": [
          "Use AWS KMS for key management",
          "Enable encryption at rest for all data stores",
          "Use TLS 1.2+ for data in transit"
        ]
      },
      "priority": "high",
      "category": "data_protection"
    }
  ]
}
```

## Maintenance

- Questions should be reviewed quarterly
- Update questions when new AWS services are released
- Align questions with latest AWS Well-Architected Framework updates
- Ensure 12-15 questions per pillar for comprehensive coverage

## Usage

Questions are automatically loaded by the `LocalQuestionLibrary` class when AWS API is unavailable.
