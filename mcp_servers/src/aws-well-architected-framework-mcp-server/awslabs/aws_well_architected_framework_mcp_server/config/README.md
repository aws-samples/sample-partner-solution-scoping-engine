# WAFR Enterprise Scoring Configuration

This directory contains JSON configuration files for the capability-based scoring system.

## Directory Structure

```
config/
├── capabilities/          # Capability definitions for each pillar
│   ├── security_capabilities.json
│   ├── reliability_capabilities.json
│   ├── performance_capabilities.json
│   ├── cost_capabilities.json
│   ├── operational_capabilities.json
│   └── sustainability_capabilities.json
├── patterns/             # Architecture pattern definitions
│   └── architecture_patterns.json
├── scoring/              # Scoring parameters
│   └── scoring_parameters.json
├── configuration_manager.py  # Configuration management class
└── README.md            # This file
```

## Configuration Files

### Capability Configurations

Each pillar has its own capability configuration file defining:
- Capability weights (importance)
- AWS services that provide each capability
- Detection patterns for identifying services
- Configuration checks for validation

**Example**: `capabilities/security_capabilities.json`
```json
{
  "encryption": {
    "weight": 0.25,
    "description": "Data encryption at rest and in transit",
    "services": [
      {
        "name": "KMS",
        "provides": "key_management",
        "coverage_factor": 0.3,
        "detection_patterns": ["AWS KMS", "Key Management Service"]
      }
    ]
  }
}
```

### Pattern Configurations

Architecture patterns define expected capabilities and scoring adjustments.

**Example**: `patterns/architecture_patterns.json`
```json
{
  "serverless": {
    "description": "Serverless architecture using managed services",
    "indicator_services": {
      "required": ["Lambda", "API Gateway"],
      "strong_indicators": ["DynamoDB", "S3"]
    },
    "scoring_adjustments": {
      "ignore_capabilities": ["ec2_auto_scaling"],
      "emphasize_capabilities": {
        "event_driven_scaling": 1.2
      }
    }
  }
}
```

### Scoring Parameters

Global scoring parameters including baselines, adjustments, and caps.

**Example**: `scoring/scoring_parameters.json`
```json
{
  "baseline_scores": {
    "security": 35,
    "reliability": 40
  },
  "score_caps": {
    "maximum": 95,
    "minimum": 0
  }
}
```

## Usage

### Loading Configuration

```python
from config import get_config_manager

# Get configuration manager (singleton)
config = get_config_manager()

# Get capability definition
encryption_cap = config.get_capability_definition('security', 'encryption')

# Get pattern definition
serverless_pattern = config.get_pattern_definition('serverless')

# Get baseline scores
baselines = config.get_baseline_scores()
```

### Hot-Reload Configuration

```python
from config import reload_config

# Reload configuration without restart
success = reload_config()
if success:
    print("Configuration reloaded successfully")
```

### Configuration Info

```python
config = get_config_manager()
info = config.get_config_info()
print(f"Config version: {info['version']}")
print(f"Capabilities loaded: {info['capabilities_loaded']}")
```

## Configuration Management

### Adding New Capabilities

1. Edit the appropriate capability JSON file
2. Add new capability definition with required fields
3. Hot-reload or restart to apply changes

### Adding New Patterns

1. Edit `patterns/architecture_patterns.json`
2. Add new pattern with indicator services and adjustments
3. Hot-reload or restart to apply changes

### Tuning Scoring

1. Edit `scoring/scoring_parameters.json`
2. Adjust baseline scores or complexity adjustments
3. Hot-reload to apply changes immediately

## Validation

Configuration files are validated on load:
- Required fields must be present
- Weights should sum to ~1.0 per pillar
- JSON syntax must be valid
- Pattern definitions must be complete

Validation errors will prevent loading and log detailed error messages.

## Best Practices

1. **Version Control**: Track all configuration changes in git
2. **Testing**: Test configuration changes in non-production first
3. **Documentation**: Document why scoring weights were chosen
4. **Backup**: Keep backups before making changes
5. **Hot-Reload**: Use hot-reload for tuning in production

## Troubleshooting

### Configuration Not Loading

Check logs for validation errors:
```
❌ Failed to load configurations: Invalid JSON in security_capabilities.json
```

### Invalid JSON

Validate JSON syntax:
```bash
python -m json.tool config/capabilities/security_capabilities.json
```

### Missing Files

Configuration manager will warn about missing files and use defaults where possible.
