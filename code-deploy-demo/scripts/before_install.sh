# Update dependencies:
yum update -y
yum install -y wget java
# Make sure a /opt/demo folder exists:
mkdir /opt/app
cd /opt/app
# stop the existing service, if it is running:
service demoapp stop
# Remove the symlink so the start script can add it:
rm -f /etc/init.d/demoapp
# Delete the old to make way for the new:
rm app.jar
