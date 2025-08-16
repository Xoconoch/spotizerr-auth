import time
import logging
import pathlib
import json
import requests
import sys
import os
import threading

# Rich library for beautiful terminal interfaces
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.rule import Rule
from rich.status import Status
from rich.text import Text

# Initialize the Rich console
console = Console()

# Define icons for consistency
class Icons:
    SPOTIFY = "🎵"
    CHECK = "✅"
    CROSS = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    ARROW = "➤"
    LOCK = "🔒"
    KEY = "🔑"
    USER = "👤"
    GEAR = "⚙️"
    DOWNLOAD = "⬇️"
    SUCCESS = "🎉"
    NETWORK = "🌐"
    CLEAN = "🧹"
    REGISTER = "👤➕"
    ADMIN = "👑"

try:
    from librespot.zeroconf import ZeroconfServer
except ImportError:
    console.print("[bold red]Error: librespot-spotizerr is not installed. Please install it with pip.[/]")
    console.print("[bold red]e.g. 'pip install -r requirements.txt' or 'pip install librespot-spotizerr'[/]")
    sys.exit(1)


def print_header():
    """Print a modern header for the application using Rich Panel."""
    header = Text.from_markup(f"""
{Icons.SPOTIFY} [bold cyan]SPOTIZERR AUTHENTICATION UTILITY[/]
[dim]Configure Spotify credentials for your Spotizerr instance[/]
    """, justify="center")
    console.print(Panel(header, border_style="cyan", expand=False))

def get_spotify_session_and_wait_for_credentials():
    """
    Starts the patched Zeroconf server. Because it's patched to be a daemon
    and not to log to the console, we can call it directly and cleanly.
    """
    credential_file = pathlib.Path("credentials.json")
    if credential_file.exists():
        console.print(f"⚠️ [yellow]Removing existing '{credential_file}'[/]")
        try:
            credential_file.unlink()
        except OSError as e:
            console.print(f"❌ [bold red]Could not remove existing 'credentials.json':[/] {e}")
            sys.exit(1)

    # Start the patched ZeroconfServer. It will run silently in the background.
    # No need to manage threads here anymore.
    zeroconf_server = ZeroconfServer.Builder().create()

    device_name = "Spotizerr Auth Tool" # A clear, static name for the user
    instructions = f"""
[bold yellow]1.[/] Open Spotify on another device.
[bold yellow]2.[/] Look for '[bold white]{device_name}[/]' in the Connect menu.
[bold yellow]3.[/] [bold]Transfer playback[/] to capture the session.
    """
    console.print(Panel(
        instructions,
        title=f"[cyan bold]{Icons.SPOTIFY} Connection Instructions[/]",
        subtitle=f"[dim]{Icons.NETWORK} Now available on your network[/]",
        border_style="cyan",
        expand=False
    ))

    with Status("Waiting for Spotify connection...", spinner="dots", console=console):
        while not (credential_file.exists() and credential_file.stat().st_size > 0):
            time.sleep(1)

    console.print(f"✅ [green]Connection successful! Credential file has been created.[/]")
    
    # We no longer need to manually close anything, the daemon will be handled
    # automatically on script exit.

# --- ALL OTHER FUNCTIONS (check_auth_status, authenticate_user, etc.) REMAIN UNCHANGED ---

def check_auth_status(base_url):
    """
    Check the authentication status of the Spotizerr instance using Rich for output.
    """
    console.print(Rule(f"[bold blue]{Icons.LOCK} Authentication Status Check[/]", style="blue"))
    
    auth_status_url = f"{base_url.rstrip('/')}/api/auth/status"
    
    with console.status(f"Checking [underline]{base_url}[/]...", spinner="dots"):
        try:
            response = requests.get(auth_status_url, timeout=10)
            response.raise_for_status()
            auth_data = response.json()
        except requests.exceptions.RequestException as e:
            console.print(f"❌ [bold red]Failed to check auth status:[/] {e}")
            return None

    auth_enabled = auth_data.get('auth_enabled', False)
    auth_icon = Icons.LOCK if auth_enabled else Icons.KEY
    status_style = "red" if auth_enabled else "green"
    
    console.print(f"{Icons.INFO} Authentication: [{status_style}]{auth_enabled}[/] {auth_icon}")
    
    if auth_enabled:
        authenticated = auth_data.get('authenticated', False)
        auth_status_icon = Icons.CHECK if authenticated else Icons.CROSS
        auth_status_style = "green" if authenticated else "red"
        
        console.print(f"{Icons.INFO} Currently authenticated: [{auth_status_style}]{authenticated}[/] {auth_status_icon}")
        console.print(f"{Icons.INFO} Registration enabled: [cyan]{auth_data.get('registration_enabled', False)}[/]")
        
        if auth_data.get('sso_enabled', False):
            providers = auth_data.get('sso_providers', [])
            console.print(f"{Icons.INFO} SSO providers: [cyan]{', '.join(providers)}[/]")
    else:
        console.print(f"✅ [green]Authentication disabled - admin privileges are automatic.[/]")
        
    return auth_data

def authenticate_user(base_url, auth_status):
    """
    Handle user authentication using Rich Prompt for choices.
    """
    if not auth_status.get('auth_enabled', False):
        console.print("✅ [green]Authentication disabled, proceeding...[/]")
        return None
    
    if auth_status.get('authenticated', False):
        console.print("✅ [green]Already authenticated.[/]")
        return "existing_token"

    console.print(Rule(f"[bold blue]{Icons.USER} User Authentication[/]", style="blue"))

    choices = ["Login to existing account"]
    if auth_status.get('registration_enabled', False):
        choices.append("Register new account")
    
    choice = Prompt.ask(
        "[bold white]Select authentication method[/]",
        choices=["Login", "Register"] if len(choices) > 1 else ["Login"],
        default="Login"
    )

    if choice == "Login":
        return login_user(base_url)
    elif choice == "Register":
        return register_user(base_url)
    else:
        console.print("❌ [bold red]Invalid choice.[/]")
        return None

def login_user(base_url):
    """
    Handle user login using Rich Prompt.
    """
    console.print(Rule(f"[bold blue]{Icons.KEY} User Login[/]", style="blue"))
    
    login_url = f"{base_url.rstrip('/')}/api/auth/login"
    
    username = Prompt.ask(f"[magenta]{Icons.ARROW}[/] Username")
    password = Prompt.ask(f"[magenta]{Icons.ARROW}[/] Password", password=True)
    
    if not username or not password:
        console.print("❌ [bold red]Username and password are required.[/]")
        return None
    
    payload = {"username": username, "password": password}
    headers = {"Content-Type": "application/json"}
    
    with console.status("Authenticating user...", spinner="dots"):
        try:
            response = requests.post(login_url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            token = data.get("access_token")
            user_info = data.get("user", {})
            
            console.print(f"✅ [green]Welcome back, [bold]{user_info.get('username', 'unknown')}[/]![/]")
            
            role = user_info.get('role', 'unknown')
            role_icon = Icons.ADMIN if role == "admin" else Icons.USER
            console.print(f"{Icons.INFO} Role: [cyan]{role}[/] {role_icon}")
            
            return token
            
        except requests.exceptions.RequestException as e:
            console.print(f"❌ [bold red]Login failed:[/] {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    console.print(f"   [red]Details: {error_data.get('error', 'Unknown error')}[/]")
                except json.JSONDecodeError:
                    console.print(f"   [red]Response: {e.response.text}[/]")
            return None

def register_user(base_url):
    """
    Handle user registration using Rich Prompt.
    """
    console.print(Rule(f"[bold blue]{Icons.REGISTER} User Registration[/]", style="blue"))
    
    register_url = f"{base_url.rstrip('/')}/api/auth/register"
    
    username = Prompt.ask(f"[magenta]{Icons.ARROW}[/] Choose username")
    email = Prompt.ask(f"[magenta]{Icons.ARROW}[/] Email address")
    password = Prompt.ask(f"[magenta]{Icons.ARROW}[/] Choose password", password=True)
    confirm_password = Prompt.ask(f"[magenta]{Icons.ARROW}[/] Confirm password", password=True)
    
    if not all([username, email, password]):
        console.print("❌ [bold red]Username, email, and password are required.[/]")
        return None
    
    if password != confirm_password:
        console.print("❌ [bold red]Passwords do not match.[/]")
        return None
    
    payload = {"username": username, "email": email, "password": password}
    
    with console.status("Creating account...", spinner="dots"):
        try:
            response = requests.post(register_url, headers={"Content-Type": "application/json"}, json=payload, timeout=10)
            response.raise_for_status()
            
            console.print(f"{Icons.SUCCESS} [green]Account created for '[bold]{username}[/]'[/]")
            console.print(f"{Icons.INFO} Please log in with your new credentials.")
            
            return login_user(base_url)
            
        except requests.exceptions.RequestException as e:
            console.print(f"❌ [bold red]Registration failed:[/] {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    console.print(f"   [red]Details: {error_data.get('error', 'Unknown error')}[/]")
                except json.JSONDecodeError:
                    console.print(f"   [red]Response: {e.response.text}[/]")
            return None

def get_auth_headers(token):
    """Get headers with authentication token if available."""
    headers = {"Content-Type": "application/json"}
    if token and token != "existing_token":
        headers["Authorization"] = f"Bearer {token}"
    return headers

def check_and_configure_api_creds(base_url, auth_token=None):
    """
    Checks and configures Spotizerr API credentials using Rich UI components.
    """
    console.print(Rule(f"[bold blue]{Icons.GEAR} Spotify API Configuration[/]", style="blue"))
    api_config_url = f"{base_url.rstrip('/')}/api/credentials/spotify_api_config"
    headers = get_auth_headers(auth_token)

    try:
        with console.status("Checking API credentials...", spinner="dots"):
            response = requests.get(api_config_url, headers=headers, timeout=10)
            response.raise_for_status()

        data = response.json()
        if data.get("client_id") and data.get("client_secret"):
            console.print("✅ [green]Spotizerr API credentials are already configured.[/]")
            return True

        console.print("⚠️ [yellow]Spotizerr server is missing Spotify API credentials (client_id/client_secret).[/]")
        console.print(f"{Icons.INFO} Get these from: [underline]https://developer.spotify.com/dashboard[/]")
        
        if not Confirm.ask("[bold]Do you want to configure them now?[/]", default=True):
            console.print(f"{Icons.INFO} Please configure API credentials on your server before proceeding.")
            return False

        new_client_id = Prompt.ask(f"[magenta]{Icons.ARROW}[/] Enter your Spotify [cyan]client_id[/]")
        new_client_secret = Prompt.ask(f"[magenta]{Icons.ARROW}[/] Enter your Spotify [cyan]client_secret[/]")

        if not new_client_id or not new_client_secret:
            console.print("❌ [bold red]Both client_id and client_secret must be provided.[/]")
            return False

        payload = {"client_id": new_client_id, "client_secret": new_client_secret}
        
        with console.status("Updating API credentials...", spinner="dots"):
            put_response = requests.put(api_config_url, headers=headers, json=payload, timeout=10)
            put_response.raise_for_status()

        console.print(f"{Icons.SUCCESS} [green]Successfully configured Spotizerr API credentials![/]")
        return True

    except requests.exceptions.RequestException as e:
        console.print(f"❌ [bold red]Failed to communicate with Spotizerr API at {api_config_url}:[/] {e}")
        if hasattr(e, 'response') and e.response is not None:
            console.print(f"   [red]Response status: {e.response.status_code}[/]")
            try:
                error_data = e.response.json()
                console.print(f"   [red]Response body: {error_data.get('error', e.response.text)}[/]")
            except json.JSONDecodeError:
                console.print(f"   [red]Response body: {e.response.text}[/]")
        return False


def main():
    """Main function for the Spotizerr auth utility."""
    print_header()
    try:
        base_url = Prompt.ask(
            f"[magenta]{Icons.ARROW}[/] Enter the base URL of your Spotizerr instance",
            default="http://localhost:7171"
        )
        if not base_url.startswith(('http://', 'https://')):
            base_url = 'http://' + base_url

        auth_status = check_auth_status(base_url)
        if auth_status is None:
            sys.exit(1)
            
        auth_token = authenticate_user(base_url, auth_status)

        if auth_status.get('auth_enabled', False) and auth_token is None:
            console.print("❌ [bold red]Authentication was required but failed. Exiting.[/]")
            sys.exit(1)

        if not check_and_configure_api_creds(base_url, auth_token):
            sys.exit(1)

        console.print(Rule(f"[bold blue]{Icons.USER} Account Configuration[/]", style="blue"))
        account_name = Prompt.ask(f"[magenta]{Icons.ARROW}[/] Enter a name for this Spotify account")
        if not account_name:
            console.print("❌ [bold red]Account name cannot be empty.[/]")
            sys.exit(1)

        region = Prompt.ask(
            f"[magenta]{Icons.ARROW}[/] Enter your Spotify region (e.g., US, DE, MX). This is the 2-letter country code"
        ).upper()
        if not region:
            console.print("❌ [bold red]Region cannot be empty.[/]")
            sys.exit(1)

        console.print(Rule(f"[bold blue]{Icons.SPOTIFY} Spotify Session Capture[/]", style="blue"))
        cred_file = pathlib.Path("credentials.json")
        if cred_file.exists():
            console.print(f"⚠️ [yellow]'{cred_file}' already exists.[/]")
            if Confirm.ask("Overwrite it by connecting to Spotify?", default=True):
                get_spotify_session_and_wait_for_credentials()
            else:
                console.print(f"{Icons.INFO} Using existing 'credentials.json'.")
        else:
            get_spotify_session_and_wait_for_credentials()
        
        if not cred_file.exists():
            console.print("❌ [bold red]Failed to obtain 'credentials.json'. Exiting.[/]")
            sys.exit(1)

        console.print(Rule(f"[bold blue]{Icons.DOWNLOAD} Uploading Credentials[/]", style="blue"))
        try:
            with open(cred_file, "r") as f:
                credentials_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            console.print(f"❌ [bold red]Could not read or parse 'credentials.json':[/] {e}")
            sys.exit(1)

        payload = {"region": region, "blob_content": credentials_data}
        api_url = f"{base_url.rstrip('/')}/api/credentials/spotify/{account_name}"
        headers = get_auth_headers(auth_token)

        with console.status(f"Registering account '[bold]{account_name}[/]' to Spotizerr...", spinner="dots"):
            try:
                response = requests.post(api_url, headers=headers, json=payload, timeout=10)
                response.raise_for_status()
                console.print(f"{Icons.SUCCESS} [green]Successfully registered/updated Spotify account in Spotizerr![/]")
                if response.text and response.headers.get("Content-Type") == "application/json":
                    console.print(f"{Icons.INFO} Server response: {response.json()}")
            except requests.exceptions.RequestException as e:
                console.print(f"❌ [bold red]Failed to call Spotizerr API:[/] {e}")
                if hasattr(e, 'response') and e.response is not None:
                     console.print(f"   [red]Status: {e.response.status_code}[/]")
                     try:
                         error_data = e.response.json()
                         console.print(f"   [red]Details: {error_data.get('error', e.response.text)}[/]")
                     except json.JSONDecodeError:
                         console.print(f"   [red]Response body: {e.response.text}[/]")
                sys.exit(1)

        console.print(Rule(f"[bold blue]{Icons.CLEAN} Cleanup[/]", style="blue"))
        if Confirm.ask("Do you want to delete 'credentials.json' now?", default=True):
            try:
                if cred_file.exists():
                    cred_file.unlink()
                    console.print("✅ [green]'credentials.json' deleted.[/]")
            except OSError as e:
                console.print(f"❌ [bold red]Error deleting 'credentials.json':[/] {e}")
        else:
            console.print(f"{Icons.INFO} 'credentials.json' was kept for future use.")
         
        console.print(f"\n[bold green]{Icons.SUCCESS} Process completed successfully![/]")
        console.print(f"[dim]Your Spotify account '{account_name}' is now configured in Spotizerr.[/]\n")
        
    except KeyboardInterrupt:
        console.print(f"\n[yellow]{Icons.WARNING} Operation cancelled by user.[/]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]An unexpected error occurred:[/bold red] {e}")
        console.print_exception(show_locals=True)
        sys.exit(1)


if __name__ == "__main__":
    main()