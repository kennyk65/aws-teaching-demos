echo "[Unit]"                     > myapp.service
echo "Description=myapp"           >> myapp.service
echo "After=syslog.target"          >>myapp.service
echo ""                              >>myapp.service
echo "[Service]"                      >>myapp.service
echo "User=myapp"                      >>myapp.service
echo "ExecStart=/var/myapp/myapp.jar"   >>myapp.service
echo "SuccessExitStatus=143"             >>myapp.service
echo ""                                   >>myapp.service
echo "[Install]"                           >>myapp.service
echo "WantedBy=multi-user.target"           >>myapp.service

