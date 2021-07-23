$Password1=$args[0]

$Account=$args[1]

$Password = "$Password1" | ConvertTo-SecureString -AsPlainText -Force

New-ADUser -Name "alice" -AccountPassword $Password -SamAccountName alice -DisplayName "alice" -EmailAddress alice@example.com -Enabled $TRUE -GivenName alice -PassThru -PasswordNeverExpires $TRUE -UserPrincipalName alice

New-ADUser -Name "bob" -AccountPassword $Password -SamAccountName bob -DisplayName "bob" -EmailAddress bob@example.com -Enabled $TRUE -GivenName bob -PassThru -PasswordNeverExpires $TRUE -UserPrincipalName bob

New-ADUser -Name "adfssvc" -AccountPassword $Password -SamAccountName adfssvc -DisplayName "adfssvc" -EmailAddress adfssvc@example.com -Enabled $TRUE -GivenName adfssvc -PassThru -PasswordNeverExpires $TRUE -UserPrincipalName adfssvc

NEW-ADGroup -name "AWS-$Account-ReadOnly" -groupscope Global

NEW-ADGroup -name "AWS-$Account-PowerUser" -groupscope Global

Add-ADGroupMember -Identity AWS-$Account-ReadOnly -Members bob

Add-ADGroupMember -Identity AWS-$Account-ReadOnly -Members alice

Add-ADGroupMember -Identity AWS-$Account-PowerUser -Members alice
