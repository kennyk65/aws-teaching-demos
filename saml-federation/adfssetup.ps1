$Password = "RANDOMPASSHERE" | ConvertTo-SecureString -AsPlainText -Force

New-ADUser -Name "alice" -AccountPassword $Password -SamAccountName alice -DisplayName "alice" -EmailAddress alice@example.com -Enabled $TRUE -GivenName alice -PassThru -PasswordNeverExpires $TRUE -UserPrincipalName alice
New-ADUser -Name "bob" -AccountPassword $Password -SamAccountName bob -DisplayName "bob" -EmailAddress bob@example.com -Enabled $TRUE -GivenName bob -PassThru -PasswordNeverExpires $TRUE -UserPrincipalName bob
New-ADUser -Name "adfssvc" -AccountPassword $Password -SamAccountName adfssvc -DisplayName "adfssvc" -EmailAddress adfssvc@example.com -Enabled $TRUE -GivenName adfssvc -PassThru -PasswordNeverExpires $TRUE -UserPrincipalName adfssvc

NEW-ADGroup -name "AWS-${AWS::AccountId}-ReadOnly" -groupscope Global
NEW-ADGroup -name "AWS-${AWS::AccountId}-PowerUser" -groupscope Global

Add-ADGroupMember -Identity AWS-${AWS::AccountId}-ReadOnly -Members bob
Add-ADGroupMember -Identity AWS-${AWS::AccountId}-ReadOnly -Members alice
Add-ADGroupMember -Identity AWS-${AWS::AccountId}-PowerUser -Members alice
Rename-Computer -NewName DC1 -Restart


# Download stuff we need:
Invoke-WebRequest -Uri "http://federationworkshopreinvent2016.s3-website-us-east-1.amazonaws.com/bootstrapping/Reset-LocalAdminPassword.ps1"  -OutFile "c:\cfn\scripts\Reset-LocalAdminPassword.ps1"
Invoke-WebRequest -Uri "http://federationworkshopreinvent2016.s3-website-us-east-1.amazonaws.com/bootstrapping/idp1cert.pfx"  -OutFile "c:\idp1cert.pfx"
Set-ExecutionPolicy RemoteSigned -Force
# DNS server should be the domain controller:
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses ${DomainController.PrivateIp}
# TODO: THIS NEXT COMMAND IS SUPPOSED TO END WITH -Restart
Rename-Computer -NewName adfsserver
# TODO: FIGURE OUT THE RESTART, IF THIS WILL EXECUTE OK, ETC.  CAN WE COMBINE RENAME WITH DOMAIN JOIN
add-computer –domainname ${DomainDNSName}  -restart
Add-KdsRootKey -EffectiveTime (Get-Date).AddHours(-10)
Install-windowsfeature adfs-federation –IncludeManagementTools
# Install certificate:
$secure = ConvertTo-SecureString "Pass@123" -AsPlainText -Force
$cert = Import-PfxCertificate -FilePath C:\idp1cert.pfx -CertStoreLocation Cert:\LocalMachine\My -Password $secure
# TODO: i'M GUESSING THE CERT
# TODO: I'M GUESSING THAT FEDERATIONSERVICENAME = SERVICEACCOUNT = idp1.example.com
# TODO: I'M GUESSING THAT GROUPSERVICEACCOUNTIDENTIFIER = FEDERATIONSERVICEDISPLAYNAME = adfssvc
Install-AdfsFarm -CertificateThumbprint $cert.Thumbprint -FederationServiceName idp1.example.com -GroupServiceAccountIdentifier EXAMPLE\adfssvc$

