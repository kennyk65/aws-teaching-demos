echo "[Unit]"                     > /etc/systemd/system/myapp.service
echo "Description=myapp"           >> /etc/systemd/system/myapp.service
echo "After=syslog.target"          >> /etc/systemd/system/myapp.service
echo ""                              >> /etc/systemd/system/myapp.service
echo "[Service]"                      >> /etc/systemd/system/myapp.service
echo "User=myapp"                      >> /etc/systemd/system/myapp.service
echo "ExecStart=/var/myapp/myapp.jar"   >> /etc/systemd/system/myapp.service
echo "SuccessExitStatus=143"             >> /etc/systemd/system/myapp.service
echo ""                                   >> /etc/systemd/system/myapp.service
echo "[Install]"                           >> /etc/systemd/system/myapp.service
echo "WantedBy=multi-user.target"           >> /etc/systemd/system/myapp.service

