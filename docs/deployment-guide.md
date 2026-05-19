## SERA IaC production deployment instructions
To deploy SERA, the following requirements must be met:

1) A public reachable domain name. Preferably this is hosted in Amazon Route 53, but if hosted at a third party, you will be required to do the domain verification manually to be able to issue the 
   certificate manager certificates. If your domain name DNS is hosted elsewhere, the easiest solution is to delegate a subdomain to this project, hosting the subdomain in Route 53 and creating NS records 
   in the root domain DNS that point to the delegated subdomain in Route 53. 
2) An RSA-2048 Key Pair for the Document retrieval via CloudFront Pre Signed URLs. Generate a key pair on a trusted computer with the following commands: 
   ## Generate the 2048-bit RSA private key
   openssl genrsa -out cloudfront-private-key.pem 2048
   ## Extract the public key from the private key
   openssl rsa -pubout -in cloudfront-private-key.pem -out cloudfront-public-key.pem
   Copy the keys and paste them into the Parameters when you deploy the 05-CloudFront stack. Ensure that you copy all of the key (Including -----BEGIN PRIVATE KEY All the way to END PRIVATE KEY----- Do not include any spaces or newline after the END PRIVATE KEY----- )
3) Access to the Anthropic Claude Sonnet-4 Model must be granted in each US region (us-east-1, us-east-2 and us-west-2) in the AWS Console. For better performance, endable cross-region inference.

It is highly recommended to use the built in instance of Amazon Cognito for Authentication, leveraging the additional security that Cognito provides. If running this as a Proof of Concept, you can use the user pool and add users manually; you also have the ability to link your IdP to Cognito via SAML for Authentication as well. In the case that you absolutely cannot use Cognito for whatever reason (again, highly recommended that you do so) in backend/config/config-template.json, you will also find example configuration items to link your IdP direrctly to the app via SAML.  

**Important:** The deploy script creates the deployment zip by cloning your branch from the remote repository, not from your local working directory. Make sure to push any local changes to your remote branch before running `deploy-sera.sh`, otherwise they will not be included in the deployed application. Note that `parameters.json` is read locally by the script and does not need to be pushed.

Deploy the cloudformation stacks in order by number. All stacks must be deployed in the same region. 

After deploying the 04-S3 stack, the `deploy-sera.sh` script automatically creates a deployment zip from your current git branch, uploads it to the sera-code-artifacts-<accountid> bucket, and sets `SeraVersion` in parameters.json to `SERA-{branch_name}`. No manual upload is required when using the deploy script.

After deploying the 07-cognito stack, add users in the Cognito console. 

After deploying the 09-bedrock stack, you must request model access to the Claude Sonnet 4 models in us-east-1, us-east-2 and us-west-2. Then configure Bedrock Model Invocation Logging, using the S3 bucket exported in CloudFormation as sera-bedrock-invocation-logs-bucket-name (CloudFormation->Exports). Sorry, as of now, this is a manual process. It is recommended that you use S3 logging only otherwise there is risk of any model invocations over 100k to not be logged.

When deleting stacks, remember to empty the S3 buckets before deleting the stack or stack deletion will fail.

## Troubleshooting Failed Deployments

The deploy script is idempotent — it skips stacks that are already in `CREATE_COMPLETE` or `UPDATE_COMPLETE` state. If a stack fails and rolls back (`ROLLBACK_COMPLETE`), you need to delete it before re-running:

```bash
aws cloudformation delete-stack --stack-name <failed-stack-name>
aws cloudformation wait stack-delete-complete --stack-name <failed-stack-name>
./deploy-sera.sh
```

The script will skip all previously completed stacks and re-attempt the failed one.

**NS Delegation Pause:** If you stop the script during the NS delegation pause (after the Route53 stack) and restart it, the Route53 stack will be skipped on re-run. Ensure your NS records are configured in the parent domain before restarting, as subsequent stacks (ACM certificate validation) depend on DNS resolution. 

## Authentication Architecture

SERA uses a dual-mode authentication system that adapts to deployment environment:

### Production Mode (AUTH_MODE: "alb")
- **ALB enforces Cognito authentication** before serving any frontend assets
- Unauthenticated users are redirected to Cognito login page
- ALB injects user information headers (`x-amzn-oidc-data`) into every request
- Backend extracts user info (email, name, groups) from ALB headers
- **Security:** No frontend assets served until authentication succeeds

### Development Mode (AUTH_MODE: "oauth2")
- Backend handles OAuth2 flow directly with Cognito
- Developers authenticate through `/api/auth` endpoint
- Session-based authentication for local testing
- Same Cognito user pool, different authentication flow

### Cognito Group Requirements
Users must be assigned to at least one of these Cognito groups:
- `sera_solutions_architect` - Solutions architects
- `sera_sales_person` - Sales team members
- `sera_sa_manager` - SA management
- `sera_sales_manager` - Sales management
- `sera_cross_customer_solutions_architect` - Cross-customer SAs
- `sera_proserve` - Professional services
- `sera_project_manager` - Project managers

### Federated Identity Support
Customers can federate their corporate IdP to Cognito:
1. Configure SAML/OIDC identity provider in Cognito User Pool
2. Map IdP groups to SERA Cognito groups
3. Users authenticate with corporate credentials
4. Cognito provides group membership in JWT claims
5. Backend enforces group-based authorization

## Deploying for local development and testing? 

Stacks not required for local development: 06-loadbalancer.yaml, 10-elasticache.yaml, 12-compute.yaml 

Create your keypair (just like above)
Install a local instance of Redis (free)
Install npm / nvm MacOS: brew install node && brew install mise for node version management 
Install uv: MacOS: brew install uv or via curl command: curl -LsSf https://astral.sh/uv/

Store your aws credentials in ~/.aws/credentials in the default profile. For most secure results, assume the ec2-role; if you are adding services, you can always create an admin role for testing but be sure you modify the ec2-role for least access privieleges if you add new services.

Set up your backend virtual environments in backend and in each mcp server root directory (everywhere you see a pyproject.toml file):
uv python pin 3.12.10
uv venv
source .venv/bin/activate
uv sync
deactivate 

Set up the backend startup script: cp systemd/start-dev.sh backend/start-dev.sh && chmod a+x backend/start-dev.sh

**Configure authentication mode in backend/config/config.json:**
- For local development: Set `"AUTH_MODE": "oauth2"` (backend handles OAuth2 directly)
- For production: Set `"AUTH_MODE": "alb"` (ALB handles Cognito authentication)

Run your local redis server in a new terminal tab: redis-server

Run the frontend in development mode in a new terminal tab: npm run build && npm run dev

Run the backend in a new terminal tab:  cd backend && ./start-dev.sh

## Backend Configuration Guide

### Configuring Personas

SERA supports multiple assistant personas, each with specialized capabilities and system prompts. Personas are configured in `backend/config/personas.py`.

#### Assistant Persona Structure

Each assistant persona has the following properties:

```python
AssistantPersona(
    name="Display Name",
    system_prompt="Detailed system prompt with instructions",
    short_description="Brief description for UI",
    knowledgebase_id="Optional Bedrock knowledge base ID",
    guardrail="Optional Bedrock guardrail ID", 
    guardrail_version="Optional guardrail version",
    allowed_groups=["list", "of", "user", "groups"],
    active="YES|NO",
    use_manual_template_substitution=False  # Use Bedrock native variables vs manual substitution
)
```

#### Adding a New Assistant Persona

1. **Define the persona** in `backend/config/personas.py`:

```python
"my_new_assistant": AssistantPersona(
    name="My New Assistant",
    system_prompt="""
    Your name is Sera, and you are an expert in [domain] speaking with {user_first_name}.
    [Add detailed instructions for the assistant's behavior and capabilities]
    """,
    short_description="Your expert for [domain]",
    knowledgebase_id="optional-kb-id",
    allowed_groups=["sera_sales_person", "sera_solutions_architect"],
    guardrail="optional-guardrail-id",
    guardrail_version="1",
    active="YES"
)
```

2. **Configure file handling** (if needed) in `backend/config/config-template.json`:

```json
"assistant_configs": {
    "my_new_assistant": {
        "enabled": true,
        "required_types": ["document_type1"],
        "optional_types": ["document_type2", "document_type3"],
        "auto_classify": true,
        "show_classification_modal": false
    }
}
```

3. **Add message enhancement** (optional) in `backend/services/message_processor.py`:

```python
class MyNewAssistantEnhancer(BaseMessageEnhancer):
    def enhance_message(self, message, intent, processed_files, file_metadata):
        # Custom message enhancement logic
        return enhanced_message

# Add to _get_persona_enhancer method:
enhancers = {
    'my_new_assistant': MyNewAssistantEnhancer(),
    # ... existing enhancers
}
```

#### Customer Persona Configuration

Customer personas represent the types of customers/partners the seller is interacting with:

```python
"customer_type_id": CustomerPersona(
    name="Customer Type Display Name",
    short_description="Description of this customer type",
    active="YES"
)
```

### File Classification and Management

File handling is configured per persona in `backend/config/config-template.json` under `FILE_CLASSIFICATION_CONFIG`.

#### File Classification Rules

Define document types in the `rules` section:

```json
"document_type_id": {
    "label": "Display Label",
    "description": "Description for users",
    "keywords": ["keyword1", "keyword2"],
    "priority_keywords": ["high", "priority", "terms"],
    "extensions": [".pdf", ".docx", ".png"],
    "icon": "icon-name",
    "required": true,
    "priority": 1
}
```

#### Per-Persona File Configuration

Configure which file types each persona can handle:

```json
"assistant_configs": {
    "persona_id": {
        "enabled": true,
        "required_types": ["must_have_these"],
        "optional_types": ["can_also_handle_these"],
        "auto_classify": true,
        "show_classification_modal": true
    }
}
```

**Configuration Options:**
- `enabled`: Whether file classification is active for this persona
- `required_types`: Document types that must be provided
- `optional_types`: Document types that can be provided but aren't required
- `auto_classify`: Automatically classify files based on keywords/extensions
- `show_classification_modal`: Show classification UI to users

#### Document Type Mapping

Map classification types to internal document types:

```json
"document_type_mapping": {
    "classification_name": "internal_document_type",
    "sow_document": "sow_document",
    "architecture_diagram": "diagram"
}
```

### Message Enhancement per Persona

When users don't provide a message but upload files, personas can enhance the empty message with context-appropriate content.

#### Creating Custom Message Enhancers

1. **Create an enhancer class** in `backend/services/message_processor.py`:

```python
class MyPersonaEnhancer(BaseMessageEnhancer):
    def enhance_message(self, message, intent, processed_files, file_metadata):
        """Enhance message for your specific persona."""
        
        if not processed_files:
            return message
            
        # Custom logic based on intent
        if intent == 'special_analysis':
            return self._handle_special_analysis(message, processed_files)
        
        # Default file handling
        return self._enhance_general_message(message, processed_files)
    
    def _handle_special_analysis(self, message, processed_files):
        """Handle special analysis intent."""
        file_links = self._create_file_links(processed_files)
        
        if not message.strip():
            message = "Please analyze these documents for [specific purpose]."
        
        return f"{message}\n\n**Documents for Analysis:**\n" + "\n".join(f"- {link}" for link in file_links)
```

2. **Register the enhancer** in the `_get_persona_enhancer` method:

```python
enhancers = {
    'my_persona_id': MyPersonaEnhancer(),
    'apn_funding_assistant': APNFundingEnhancer(),
    'aws_solutions_assistant': AWSSolutionsEnhancer(),
}
```

#### Built-in Enhancement Features

**File Link Creation:**
- Images: `![filename.png](s3://url?versionId=xxx)` (inline display)
- Documents: `[filename.pdf](s3://url?versionId=xxx)` (download links)

**Intent-Based Enhancement:**
- Different enhancement logic based on user intent
- Special handling for specific workflows (e.g., POC funding review)

**Structured File Presentation:**
- Organized file lists by classification type
- Professional formatting for business contexts
- Contextual messaging when no user message provided

### User Group and Access Control

Control persona access using the `allowed_groups` property:

```python
allowed_groups=["sera_sales_person", "sera_solutions_architect", "sera_sa_manager"]
```

**Available Groups:**
- `sera_sales_person`: Sales team members
- `sera_solutions_architect`: Technical architects  
- `sera_sales_manager`: Sales management
- `sera_sa_manager`: SA management
- `sera_cross_customer_solutions_architect`: Cross-customer SAs
- `sera_proserve`: Professional services
- `sera_project_manager`: Project managers

### Template Variable Substitution

Personas support dynamic template variables in system prompts:

**Bedrock Native Variables** (`use_manual_template_substitution=False`):
```
{user_first_name}, {customer_persona}, {interaction_method}
```

**Manual Substitution** (`use_manual_template_substitution=True`):
```
{{user_first_name}}, {{customer_persona}}, {{interaction_method}}
```

Use Bedrock native variables for better performance and built-in validation.

### Configuration Examples

#### Example: Adding a Custom Technical Assistant

Here's a complete example of adding a new technical assistant persona:

**1. Add to `backend/config/personas.py`:**
```python
"technical_support_assistant": AssistantPersona(
    name="Technical Support Assistant",
    system_prompt="""
    Your name is Sera, and you are a technical support specialist speaking with {user_first_name}.
    You help troubleshoot AWS technical issues and provide implementation guidance.
    The user is interacting with a {customer_persona} via {interaction_method}.
    
    When users upload log files or error reports, analyze them systematically:
    1. Identify the error patterns and root causes
    2. Provide step-by-step troubleshooting steps
    3. Suggest preventive measures and best practices
    4. Offer alternative solutions if the primary approach fails
    """,
    short_description="Your expert for AWS technical troubleshooting",
    knowledgebase_id="kb-technical-docs-123",
    allowed_groups=["sera_solutions_architect", "sera_proserve"],
    guardrail="technical-support-guardrail",
    guardrail_version="1",
    active="YES",
    use_manual_template_substitution=False
)
```

**2. Configure file handling in `backend/config/config-template.json`:**
```json
"technical_support_assistant": {
    "enabled": true,
    "required_types": ["technical_document"],
    "optional_types": ["architecture_diagram", "other"],
    "auto_classify": true,
    "show_classification_modal": false
}
```

**3. Add custom message enhancer in `backend/services/message_processor.py`:**
```python
class TechnicalSupportEnhancer(BaseMessageEnhancer):
    def enhance_message(self, message, intent, processed_files, file_metadata):
        if not processed_files:
            return message
        
        file_links = self._create_file_links(processed_files)
        
        if not message.strip():
            message = "I've uploaded technical files for analysis. Please help me troubleshoot the issues."
        
        enhanced_message = f"{message}\n\n**Technical Files for Analysis:**\n"
        
        for i, file_link in enumerate(file_links, 1):
            enhanced_message += f"{i}. {file_link}\n"
        
        enhanced_message += "\nPlease analyze these files and provide troubleshooting recommendations."
        return enhanced_message

# Register in _get_persona_enhancer method:
enhancers = {
    'technical_support_assistant': TechnicalSupportEnhancer(),
    'apn_funding_assistant': APNFundingEnhancer(),
    'aws_solutions_assistant': AWSSolutionsEnhancer(),
}
```

#### Example: Custom File Classification Rule

Add a new document type for log files:

```json
"log_file": {
    "label": "Log File",
    "description": "System logs, application logs, or error reports",
    "keywords": ["log", "error", "debug", "trace", "exception"],
    "priority_keywords": ["error", "exception", "failed", "timeout"],
    "extensions": [".log", ".txt", ".json"],
    "icon": "file-text",
    "required": false,
    "priority": 2
}
```

### Best Practices

#### Persona Design
- **Keep system prompts focused**: Each persona should have a clear, specific role
- **Use consistent naming**: Follow the pattern `{domain}_{type}_assistant`
- **Test with real scenarios**: Validate personas with actual use cases before deployment
- **Monitor performance**: Track conversation success rates and user satisfaction

#### File Classification
- **Order matters**: Higher priority classifications are checked first
- **Keywords are case-insensitive**: The system automatically handles case matching
- **Use specific extensions**: Be explicit about supported file types
- **Test auto-classification**: Verify that files are classified correctly

#### Message Enhancement
- **Handle empty messages gracefully**: Always provide meaningful context when users upload files without text
- **Be consistent with formatting**: Use similar markdown patterns across enhancers
- **Log for debugging**: Include appropriate logging for troubleshooting
- **Consider file types**: Handle images differently from documents

#### Security Considerations
- **Validate user groups**: Always check `allowed_groups` for access control
- **Sanitize file content**: Ensure uploaded files are safe to process
- **Use guardrails**: Implement Bedrock guardrails for sensitive personas
- **Monitor usage**: Track persona usage and detect anomalies

### Troubleshooting

#### Common Issues

**Persona not appearing in UI:**
- Check `active` is set to `"YES"`
- Verify user has required group membership
- Ensure no syntax errors in `personas.py`

**File classification not working:**
- Verify file extension matches `extensions` list
- Check keyword matching in filename or content
- Review `auto_classify` setting for the persona

**Message enhancement not applied:**
- Confirm enhancer is registered in `_get_persona_enhancer`
- Check for errors in enhancer logic
- Verify `assistant_persona_id` matches exactly

**Template variables not substituting:**
- Check `use_manual_template_substitution` setting
- Verify variable names match exactly (case-sensitive)
- Ensure variables are provided in the request context 