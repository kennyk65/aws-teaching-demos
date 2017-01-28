#!/bin/bash
yum update -y
wget https://s3-us-west-2.amazonaws.com/kk-site/spring-cloud-aws-environment-demo-1.war
sudo java -jar spring-cloud-aws-environment-demo-1.war --server.port=80