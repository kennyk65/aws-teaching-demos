$Password = "RANDOMPASSHERE" | ConvertTo-SecureString -AsPlainText -Force

New-ADUser -Name "alice" -AccountPassword $Password -SamAccountName alice -DisplayName "alice" -EmailAddress alice@example.com -Enabled $TRUE -GivenName alice -PassThru -PasswordNeverExpires $TRUE -UserPrincipalName alice
New-ADUser -Name "bob" -AccountPassword $Password -SamAccountName bob -DisplayName "bob" -EmailAddress bob@example.com -Enabled $TRUE -GivenName bob -PassThru -PasswordNeverExpires $TRUE -UserPrincipalName bob
New-ADUser -Name "adfssvc" -AccountPassword $Password -SamAccountName adfssvc -DisplayName "adfssvc" -EmailAddress adfssvc@example.com -Enabled $TRUE -GivenName adfssvc -PassThru -PasswordNeverExpires $TRUE -UserPrincipalName adfssvc
