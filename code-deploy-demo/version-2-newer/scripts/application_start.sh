# Run the application as a service:
cd /var/app
mv *.jar app.jar
chmod +x app.jar
systemctl start spring-boot-app