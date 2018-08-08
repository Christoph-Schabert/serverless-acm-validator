# serverless-acm-validator


Build:
AWS_PROFILE=private sam package --template-file template.yml --s3-bucket sam-schabert --output-template packaged-template.yaml
AWS_PROFILE=private sam deploy --no-execute-changeset --capabilities=CAPABILITY_IAM --template-file packaged-template.yaml --stack-name acm