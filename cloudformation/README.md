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

After deploying the 09-bedrock stack, configure Bedrock Model Invocation Logging, using the S3 bucket exported in CloudFormation as sera-bedrock-invocation-logs-bucket-name (CloudFormation->Exports). Sorry, as of now, this is a manual process. It is recommended that you use S3 logging only otherwise there is risk of any model invocations over 100k to not be logged.

When deleting stacks, remember to empty the S3 buckets before deleting the stack or stack deletion will fail. 

## Deploying for local development and testing? 

Stacks not required for local development: 06-loadbalancer.yaml, 10-elasticache.yaml, 12-compute.yaml 

Create your keypair (just like above)
Install a local instance of Redis (free)
Install npm /nvm MacOS: brew install node && brew install mise for node version management 
Install uv: MacOS: brew install uv or via curl command: curl -LsSf https://astral.sh/uv/

Store your aws credentials in ~/.aws/credentials in the default profile. For most secure results, assume the ec2-role. 

Run the frontend in development mode: npm run build && npm run dev

Set up the backend startup script: cp systemd/start-dev.sh backend/start-dev.sh $$ chmod a+x backend/start-dev.sh

Run the backend:  cd backend && ./start-dev.sh 