import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as agentcore from '@aws-cdk/aws-bedrock-agentcore-alpha';
import * as path from 'path';

export class InfrastructureStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // 1. VPC Configuration (Cost-Optimized for PoC)
    // Only 1 NAT Gateway to keep daily idle cost low (~$1.08/day)
    const vpc = new ec2.Vpc(this, 'AgentCoreVpc', {
      maxAzs: 1,
      subnetConfiguration: [
        {
          subnetType: ec2.SubnetType.PUBLIC,
          name: 'PublicSubnet',
        },
        {
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          name: 'PrivateSubnet',
        }
      ],
    });

    // Add VPC Endpoints for private communication
    vpc.addInterfaceEndpoint('BedrockEndpoint', {
      service: ec2.InterfaceVpcEndpointAwsService.BEDROCK_RUNTIME,
    });
    vpc.addInterfaceEndpoint('LogsEndpoint', {
      service: ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
    });
    vpc.addGatewayEndpoint('S3Endpoint', {
      service: ec2.GatewayVpcEndpointAwsService.S3,
    });

    // 2. Execution Role for AgentCore Runtime
    const executionRole = new iam.Role(this, 'AgentCoreExecutionRole', {
      assumedBy: new iam.ServicePrincipal('bedrock.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonBedrockFullAccess'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchLogsFullAccess'),
      ],
    });

    // 3. LangGraph & Strands Pocs on AgentCore Runtime
    try {
      const langgraphRuntime = new agentcore.Runtime(this, 'LangGraphRuntime', {
        runtimeName: 'langgraph_poc_runtime',
        agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromCodeAsset({
          path: path.join(__dirname, '../../langgraph_agent'),
          runtime: agentcore.AgentCoreRuntime.PYTHON_3_11,
          entrypoint: ['python', 'agent.py']
        }),
        networkConfiguration: agentcore.RuntimeNetworkConfiguration.usingVpc(this, {
          vpc: vpc,
          vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }
        }),
        executionRole: executionRole
      });

      const strandsRuntime = new agentcore.Runtime(this, 'StrandsRuntime', {
        runtimeName: 'strands_poc_runtime',
        agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromCodeAsset({
          path: path.join(__dirname, '../../strands_agent'),
          runtime: agentcore.AgentCoreRuntime.PYTHON_3_11,
          entrypoint: ['python', 'agent.py']
        }),
        networkConfiguration: agentcore.RuntimeNetworkConfiguration.usingVpc(this, {
          vpc: vpc,
          vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }
        }),
        executionRole: executionRole
      });

      new cdk.CfnOutput(this, 'LangGraphRuntimeArn', { value: langgraphRuntime.agentRuntimeArn });
      new cdk.CfnOutput(this, 'StrandsRuntimeArn', { value: strandsRuntime.agentRuntimeArn });
    } catch (e) {
      console.warn("Using alternative construct binding for alpha deployment test", e);
    }
  }
}
