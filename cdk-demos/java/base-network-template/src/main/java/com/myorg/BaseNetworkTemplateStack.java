package com.myorg;

import java.util.Arrays;

import software.amazon.awscdk.core.CfnParameter;
import software.amazon.awscdk.core.Construct;
import software.amazon.awscdk.core.Stack;
import software.amazon.awscdk.core.StackProps;
import software.amazon.awscdk.services.ec2.Vpc;

public class BaseNetworkTemplateStack extends Stack {
    public BaseNetworkTemplateStack(final Construct scope, final String id) {
        this(scope, id, null);
    }

    public BaseNetworkTemplateStack(final Construct scope, final String id, final StackProps props) {
        super(scope, id, props);

        // The code that defines your stack goes here   
        
        //	TODO: FIGURE OUT HOW TO CONTROL # OF AZS USED WITH THIS PARAMETER.
        CfnParameter numberOfAzs = CfnParameter.Builder.create(this, "NumberOfAZs")
        		.type("Number")
        		.allowedValues( Arrays.asList( "1","2","3") )
        		.description("How many Availability Zones do you wish to utilize?")
        		.defaultValue("2")
        		.build();

        // TODO: FIGURE OUT HOW TO CONTROL PRIVATE SUBNET CREATION WITH THIS PARAMETER.
        CfnParameter makePrivateSubnets = CfnParameter.Builder.create(this, "makePrivateSubnets")
        		.type("String")
        		.allowedValues( Arrays.asList( "true","false") )
        		.description("Do you want to generate private subnets or not?")
        		.defaultValue("true")
        		.build();
        
        //	TODO: FIGURE OUT HOW TO DO CONDITIONS.  APPARENTLY, IN JAVA YOU CAN CREATE THEM, BUT NOT REFERENCE THEM.
        
//        CfnCondition condition = CfnCondition.Builder.create(this,"buildPrivateSubnets")
//        		.expression(
//        			new ICfnConditionExpression() {
//						
//						@Override
//						public Object resolve(IResolveContext context) {
//							// TODO Auto-generated method stub
//							return null;
//						}
//						
//						@Override
//						public List<String> getCreationStack() {
//							// TODO Auto-generated method stub
//							return null;
//						}
//						
//						
//					};	
//        				)
//        		.build()

        //	TODO: FIND OUT HOW TO DETERMINE CURRENT REGION.  THIS VALUE IS NULL:
//        System.out.println("CURRENT REGION: " + props.getEnv().getRegion());
        
        // THIS IS LOW-LEVEL RESOURCE CREATION.  EQUIVALENT TO REGULAR CLOUD FORMATION EXCEPT HARDER.
        
//        CfnVPC v = CfnVPC.Builder.create(this, "vpc")
//        		.cidrBlock("10.0.0.0/16")
//        		.enableDnsHostnames(true)
//        		.enableDnsSupport(true)
//        		.build();
//
//        CfnInternetGateway igw = CfnInternetGateway.Builder.create(this,"igw").build();
//        
//        CfnVPCGatewayAttachment attach = CfnVPCGatewayAttachment.Builder.create(this,"attach")
//        		.internetGatewayId(igw.getLogicalId())
//        		.vpcId(v.getLogicalId())
//        		.build();
//
//        CfnSubnet pub1 = CfnSubnet.Builder.create(this, "pub1")
////        		.availabilityZone( Fn.getAzs(props.getEnv().getRegion()).get(0) )	// TODO: PRODUCES NULL POINTER
//        		.availabilityZone( "us-west-2a" )	
//        		.cidrBlock("10.1.0.0/24")
//        		.vpcId(v.getLogicalId())
//        		.build();
//        
//        //	TODO: FIGURE OUT HOW TO CONTROL WITH PARAMETER OR CONDITION.
//        CfnSubnet pub2 = CfnSubnet.Builder.create(this, "pub2")
////        		.availabilityZone( Fn.getAzs(props.getEnv().getRegion()).get(1) )	// TODO: PRODUCES NULL POINTER
//        		.availabilityZone( "us-west-2b" )	
//        		.cidrBlock("10.2.0.0/24")
//        		.vpcId(v.getLogicalId())
//        		.build();
//        
//        //	TODO: FIGURE OUT HOW TO CONTROL WITH PARAMETER OR CONDITION.
//        CfnSubnet pri1 = CfnSubnet.Builder.create(this, "priv1")
////        		.availabilityZone( Fn.getAzs(props.getEnv().getRegion()).get(0) )	// TODO: PRODUCES NULL POINTER
//        		.availabilityZone( "us-west-2a" )	
//        		.cidrBlock("10.3.0.0/24")
//        		.vpcId(v.getLogicalId())
//        		.build();
//        
//        //	TODO: FIGURE OUT HOW TO CONTROL WITH PARAMETER OR CONDITION.
//        CfnSubnet pri2 = CfnSubnet.Builder.create(this, "priv2")
////        		.availabilityZone( Fn.getAzs(props.getEnv().getRegion()).get(1) )	// TODO: PRODUCES NULL POINTER
//        		.availabilityZone( "us-west-2b" )	
//        		.cidrBlock("10.4.0.0/24")
//        		.vpcId(v.getLogicalId())
//        		.build();
//        
        
        
//        //  TODO; COME UP WITH A WAY TO DO INPUT PARAMETERS:
//        int numberofzones = 3;
//
//        //	TODO: FIGURE OUT HOW TO CONTROL SUBNET NAMES WITH CIDR AND AZ ASSOCIATION
//        
//        List<SubnetConfiguration> subs = new ArrayList<>();
//        subs.add(
//            	new SubnetConfiguration() {
//    				@Override
//    				public String getName() {
//    					return "i-say-public";
//    				}
//    				@Override
//    				public SubnetType getSubnetType() {
//    					return SubnetType.PUBLIC;
//    				}
//    				
//    				
//            	}	
//            );
//        subs.add(
//            	new SubnetConfiguration() {
//    				@Override
//    				public String getName() {
//    					return "i-say-private";
//    				}
//    				@Override
//    				public SubnetType getSubnetType() {
//    					return SubnetType.PRIVATE;
//    				}
//    				
//            	}	
//            );
//

        //	TODO: IF YOU USE THE INPUT PARAMETER numberOfAzs, It suddenly removes all NATs
        //  TODO: Can't control number of AZs, even with hard-coded parameter.
        //	TODO:  CAN'T USE THIS UNLESS YOU WANT IGW.
        
        Vpc vpc = Vpc.Builder.create(this, "myVPC")
        		.cidr("10.0.0.0/16")
        		.enableDnsHostnames(true)
        		.enableDnsSupport(true)
        		.maxAzs(3)			// Can only build 1 or 2 vpcs, not 3!!!	
//        		.subnetConfiguration(subs)		//	this only controls broad subnet settings.

        		.build();
     }
}
