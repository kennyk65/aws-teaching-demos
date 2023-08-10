import boto3

# create clients
ecs = boto3.client('ecs')
ec2 = boto3.client('ec2')
iam = boto3.client('iam')


# write a function to get the VPC ID of the default subnet
def get_default_vpc_id():   
    response = ec2.describe_vpcs(
        Filters=[
            {
                'Name': 'isDefault',
                'Values': ['true']
            }
        ]
    )
    return response['Vpcs'][0]['VpcId']


# write a function to return the public subnet ids of the given VPC ID  
def get_public_subnet_ids(vpcId):
    # get the subnet ids
    response = ec2.describe_subnets(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [vpcId]
            }
        ]
    )
    # get the subnet ids
    subnet_ids = [subnet['SubnetId'] for subnet in response['Subnets']]

    # remove any subnet_ids which are not public
    for subnet_id in subnet_ids:
        response = ec2.describe_subnets(
            SubnetIds=[subnet_id]
        )
        if response['Subnets'][0]['MapPublicIpOnLaunch'] == False:
            subnet_ids.remove(subnet_id)

    return subnet_ids


# write a function to create a security group.  Use a parameter for the VPC id.
def create_security_group(vpcId):

    # find the security group id of the security group named 'allow-http'
    response = ec2.describe_security_groups(
        Filters=[
            {   
                'Name': 'group-name',
                'Values': ['allow-http']
            }
        ]
    )
    # if a security group named 'allow-http' exists, return its id
    if len(response['SecurityGroups']) > 0:
        security_group_id = response['SecurityGroups'][0]['GroupId']
        print('Security group named "allow-http" already exists.  Security group id: ' + security_group_id)
        return security_group_id

    # if the vpcId parameter is missing, get the id of the default VPC
    if vpcId == None:
        vpcId = get_default_vpc_id()    

    # create a security group in the given vpcId
    response = ec2.create_security_group(
        Description='Allow http from anywhere',
        GroupName='allow-http',
        VpcId=vpcId
        )

    # get the security group id
    security_group_id = response['GroupId']

    # add a rule to the above security group allowing ingress for http on port 80 from anywhere.
    ec2.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions=[
            {'IpProtocol': 'tcp',
            'FromPort': 80,
            'ToPort': 80,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ])

    # print a message to the use
    print('Security group created.  Security group id: ' + security_group_id)
    return security_group_id;


# write a function to create a cluster.  Use a parameter for cluster name.
def create_cluster(clusterName):

    # check to see if the given cluster exists.  If so return its ARN.
    response = ecs.list_clusters()
    for clusterArn in response['clusterArns']:
        if clusterName in clusterArn:
            print('Cluster named "' + clusterName + '" already exists.  Cluster ARN: ' + clusterArn)
            return clusterArn
        
    response = ecs.create_cluster(clusterName=clusterName)
    cluster_arn = response['cluster']['clusterArn']
    print('Cluster created.  Cluster ARN: ' + cluster_arn)
    return cluster_arn

# write a function to create a task definition to run public.ecr.aws/kkrueger/flask-api exposed on port 80 in Fargate
def create_task_definition():

    # get the vpcId of the default VPC
    vpcId = get_default_vpc_id()

    # get the ARN of the IAM role named ecsTaskExecutionRole
    response = iam.get_role(
        RoleName='ecsTaskExecutionRole'
        )
    roleArn = response['Role']['Arn']


    # get the task definition ARN
    response = ecs.register_task_definition(
        family='flask-api',
        containerDefinitions=[
            {
                'name': 'flask-api',
                'image': 'public.ecr.aws/kkrueger/spring-cloud-aws-environment-demo:latest',
                'portMappings': [
                    {                    
                        'containerPort': 80,
                        'hostPort': 80  }],
                'essential': True,
            }
            ],
            cpu='256',
            memory='512',
            networkMode='awsvpc',
            requiresCompatibilities=[ 'FARGATE' ],
            executionRoleArn=roleArn, 
            )

    # Get the task definition ARN
    return response['taskDefinition']['taskDefinitionArn']


# write a function to run a task using the task definition created in the previous step using the cluster created above.
def run_task():
    # get the public subnets of the default VPC
    vpcId = get_default_vpc_id()
    subnet_ids = get_public_subnet_ids(vpcId)

    # create a security group in the given VPC
    security_group_id = create_security_group(vpcId)

    # create the cluster and return the cluster ARN
    cluster_arn = create_cluster('flask-api-cluster')
        
    # run a task using the task definition created in the previous step.
    response = ecs.run_task(
        cluster=cluster_arn,
        count=1,
        taskDefinition=create_task_definition(),
        launchType='FARGATE',
        networkConfiguration={
            'awsvpcConfiguration': {
                'subnets': [
                    subnet_ids[0],
                    subnet_ids[1]
                ],
                'securityGroups': [security_group_id],
                'assignPublicIp': 'ENABLED'
            }
        }
    )
    return response['tasks'][0]['taskArn']




# run the task and get the task ARN
task_arn = run_task()

# wait up to 10 seconds for the task to start running
print('Waiting for task to start running...')
ecs.get_waiter('tasks_running').wait(
    cluster='flask-api-cluster',
    tasks=[task_arn],
    WaiterConfig={
        'Delay': 5,
        'MaxAttempts': 10
        }
    )

print('task should be ready now')

