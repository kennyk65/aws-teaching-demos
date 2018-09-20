# Run the application as a service:
# Make a symlink to the JAR as described here:  https://docs.spring.io/spring-boot/docs/current/reference/htmlsingle/#deployment-service
cd /opt/app/
mv *.jar app.jar
chmod +x app.jar
ln -s /opt/app/app.jar /etc/init.d/demoapp
service demoapp start

