#Inactive DynamoDB table finding and change to On-Demand I/O mode

## pre-requisites
1. Install serverless framework using npm.
2. Install npm serverless modules listed on package.json file - namely 'serverless-plugin-additional-stacks' and 'serverless-python-requirements'
3. Install python 3.8 version

##Deployment
Deploy the infrastructure stack first (additionalstack)
```commandline
sls deploy additionalstacks -s <stage-environment> -r <aws-region-id>
``` 

Deploy the main stack using general sls deploy command
```commandline
sls deploy --skip-additionalstacks -s <stage-environment> -r <aws-region-id> 
```
