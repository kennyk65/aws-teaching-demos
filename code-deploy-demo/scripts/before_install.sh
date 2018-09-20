# Make sure a /opt/demo folder exists:
mkdir /opt/app
cd /opt/app
# Delete the old to make way for the new:
rm app.jar
# Update dependencies:
yum update -y
yum install -y wget java