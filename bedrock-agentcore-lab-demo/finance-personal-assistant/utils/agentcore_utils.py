import boto3
from boto3.session import Session
import secrets
import string
import json
from botocore.exceptions import ClientError


def generate_secure_password(length=16):
    """Generate a secure random password meeting Cognito requirements."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    # Ensure it meets requirements (at least one uppercase, lowercase, digit, special)
    if (any(c.isupper() for c in password) and
        any(c.islower() for c in password) and
        any(c.isdigit() for c in password) and
        any(c in "!@#$%^&*()" for c in password)):
        return password
    return generate_secure_password(length)  # Retry if requirements not met


def setup_cognito_user_pool():
    boto_session = Session()
    region = boto_session.region_name
    # Initialize Cognito client
    cognito_client = boto3.client("cognito-idp", region_name=region)
    try:
        # Create User Pool with strong password policy
        user_pool_response = cognito_client.create_user_pool(
            PoolName="agentpool",
            Policies={
                "PasswordPolicy": {
                    "MinimumLength": 12,  # Increased from 8
                    "RequireUppercase": True,
                    "RequireLowercase": True,
                    "RequireNumbers": True,
                    "RequireSymbols": True,
                    "TemporaryPasswordValidityDays": 1  # Expire temp passwords quickly
                }
            },
            # Disable self-registration - only admins can create users
            AdminCreateUserConfig={
                "AllowAdminCreateUserOnly": True
            },
            # Add MFA configuration (optional but recommended)
            # MfaConfiguration="OPTIONAL",
            # Account recovery via email (MFA disabled for lab simplicity)
            AccountRecoverySetting={
                'RecoveryMechanisms': [
                    {
                        'Priority': 1,
                        'Name': 'verified_email'
                    }
                ]
            }
        )
        pool_id = user_pool_response["UserPool"]["Id"]
        # Create App Client
        app_client_response = cognito_client.create_user_pool_client(
            UserPoolId=pool_id,
            ClientName="MCPServerPoolClient",
            GenerateSecret=False,
            ExplicitAuthFlows=["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"],
        )
        client_id = app_client_response["UserPoolClient"]["ClientId"]
        
        # Generate secure credentials
        username = f"labuser-{secrets.token_hex(4)}"
        temp_password = generate_secure_password()
        permanent_password = generate_secure_password()
        
        # Create User
        cognito_client.admin_create_user(
            UserPoolId=pool_id,
            Username=username,
            TemporaryPassword=temp_password,
            MessageAction="SUPPRESS",
        )
        # Set Permanent Password
        cognito_client.admin_set_user_password(
            UserPoolId=pool_id,
            Username=username,
            Password=permanent_password,
            Permanent=True,
        )
        # Authenticate User and get Access Token
        auth_response = cognito_client.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": permanent_password},
        )
        bearer_token = auth_response["AuthenticationResult"]["AccessToken"]
        
        # Store credentials in AWS Secrets Manager
        secrets_client = boto3.client("secretsmanager", region_name=region)
        secret_name = f"agentcore-lab-credentials-{secrets.token_hex(4)}"
        
        try:
            secret_value = json.dumps({
                "username": username,
                "password": permanent_password,
                "pool_id": pool_id,
                "client_id": client_id
            })
            
            secrets_client.create_secret(
                Name=secret_name,
                Description="AgentCore Lab Cognito User Credentials",
                SecretString=secret_value,
                Tags=[
                    {"Key": "Purpose", "Value": "AgentCoreLab"},
                    {"Key": "ManagedBy", "Value": "AgentCoreUtils"}
                ]
            )
            print(f"✓ Credentials stored in AWS Secrets Manager: {secret_name}")
        except ClientError as e:
            print(f"Warning: Could not store credentials in Secrets Manager: {e}")
            print("Credentials will only be displayed below.")
        
        # Output the required values
        print("\n" + "="*70)
        print("⚠️  IMPORTANT: SAVE THESE CREDENTIALS NOW!")
        print("="*70)
        print(f"Username: {username}")
        print(f"Password: {permanent_password}")
        print(f"Secret Name: {secret_name}")
        print(f"Pool ID: {pool_id}")
        print(
            f"Discovery URL: https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/openid-configuration"
        )
        print(f"Client ID: {client_id}")
        print(f"Bearer Token: {bearer_token}")
        print("="*70)
        print("⚠️  These credentials will NOT be shown again!")
        print("    Retrieve them later using: retrieve_credentials_from_secrets_manager()")
        print("="*70 + "\n")

        # Return values if needed for further processing
        return {
            "pool_id": pool_id,
            "client_id": client_id,
            "bearer_token": bearer_token,
            "discovery_url": f"https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/openid-configuration",
            "username": username,
            "password": permanent_password,
            "secret_name": secret_name,
        }
    except Exception as e:
        print(f"Error: {e}")
        return None


def retrieve_credentials_from_secrets_manager(secret_name):
    """
    Retrieve stored credentials from AWS Secrets Manager.
    
    Args:
        secret_name: The name of the secret to retrieve
        
    Returns:
        dict: Dictionary containing username, password, pool_id, and client_id
    """
    boto_session = Session()
    region = boto_session.region_name
    secrets_client = boto3.client("secretsmanager", region_name=region)
    
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        credentials = json.loads(response["SecretString"])
        print(f"✓ Retrieved credentials from Secrets Manager: {secret_name}")
        return credentials
    except ClientError as e:
        print(f"Error retrieving credentials from Secrets Manager: {e}")
        return None


def reauthenticate_user(client_id, username=None, password=None, secret_name=None):
    """
    Reauthenticate a user and get a new bearer token.
    
    Args:
        client_id: The Cognito client ID
        username: The username (optional if secret_name provided)
        password: The password (optional if secret_name provided)
        secret_name: The Secrets Manager secret name (optional)
        
    Returns:
        str: New bearer token
    """
    boto_session = Session()
    region = boto_session.region_name
    
    # If secret_name provided, retrieve credentials from Secrets Manager
    if secret_name and (not username or not password):
        credentials = retrieve_credentials_from_secrets_manager(secret_name)
        if credentials:
            username = credentials.get("username")
            password = credentials.get("password")
        else:
            raise ValueError("Could not retrieve credentials from Secrets Manager")
    
    if not username or not password:
        raise ValueError("Username and password are required. Provide them directly or via secret_name.")
    
    # Initialize Cognito client
    cognito_client = boto3.client("cognito-idp", region_name=region)
    
    try:
        # Authenticate User and get Access Token
        auth_response = cognito_client.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )
        bearer_token = auth_response["AuthenticationResult"]["AccessToken"]
        print("✓ Successfully reauthenticated user")
        return bearer_token
    except ClientError as e:
        print(f"Error during reauthentication: {e}")
        raise


def disable_self_registration(pool_id=None):
    """
    Disable self-registration on a Cognito User Pool (admin-only user creation).
    
    Args:
        pool_id: The pool ID to update (optional, will find agentpool if not provided)
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    boto_session = Session()
    region = boto_session.region_name
    cognito_client = boto3.client("cognito-idp", region_name=region)
    
    try:
        # If no pool_id provided, find agentpool
        if not pool_id:
            response = cognito_client.list_user_pools(MaxResults=60)
            for pool in response.get("UserPools", []):
                if pool.get("Name") == "agentpool":
                    pool_id = pool.get("Id")
                    break
            
            if not pool_id:
                print("agentpool not found")
                return False
        
        # Update the user pool to disable self-registration
        print(f"Disabling self-registration for User Pool: {pool_id}")
        cognito_client.update_user_pool(
            UserPoolId=pool_id,
            AdminCreateUserConfig={
                "AllowAdminCreateUserOnly": True
            }
        )
        print(f"✓ Successfully disabled self-registration for User Pool: {pool_id}")
        print("  Only administrators can now create users")
        return True
        
    except Exception as e:
        print(f"Error updating User Pool: {e}")
        return False


def delete_cognito_user_pool(pool_id=None):
    """
    Delete a Cognito User Pool by ID, or find and delete agentpool if no ID provided.

    Args:
        pool_id: The pool ID to delete (optional)

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    boto_session = Session()
    region = boto_session.region_name
    cognito_client = boto3.client("cognito-idp", region_name=region)

    try:
        # If no pool_id provided, find agentpool
        if not pool_id:
            response = cognito_client.list_user_pools(MaxResults=60)
            for pool in response.get("UserPools", []):
                if pool.get("Name") == "agentpool":
                    pool_id = pool.get("Id")
                    break

            if not pool_id:
                print("agentpool not found")
                return False

        # Delete the user pool
        print(f"Deleting Cognito User Pool: {pool_id}")
        cognito_client.delete_user_pool(UserPoolId=pool_id)
        print(f"Successfully deleted User Pool: {pool_id}")
        return True

    except Exception as e:
        print(f"Error deleting User Pool: {e}")
        return False
