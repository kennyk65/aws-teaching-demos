# Update dependencies:
yum update -y
yum install wget java-17-amazon-corretto -y
# Make sure a /var/app folder exists: 
mkdir /var/app
cd /var/app
# stop the existing service, if it is running:
systemctl stop spring-boot-app
# Delete the old to make way for the new:
rm -f app.jar