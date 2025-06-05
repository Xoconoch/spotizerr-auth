import time
import logging
import pathlib
import json
import requests
import sys

class Colors:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

try:
    from librespot.zeroconf import ZeroconfServer
except ImportError:
    logging.error("librespot-spotizerr is not installed. Please install it with pip.")
    logging.error("e.g. 'pip install -r requirements.txt' or 'pip install librespot-spotizerr'")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_spotify_session_and_wait_for_credentials():
    """
    Starts Zeroconf server and waits for librespot to store credentials.
    """
    credential_file = pathlib.Path("credentials.json")
    
    if credential_file.exists():
        logging.info(f"Removing existing '{credential_file}'")
        try:
            credential_file.unlink()
        except OSError as e:
            logging.error(f"Could not remove existing 'credentials.json': {e}")
            sys.exit(1)

    zs = ZeroconfServer.Builder().create()
    device_name = "librespot-spotizerr"
    # This is a bit of a hack to get the device name, but it's useful for the user.
    if hasattr(zs, '_ZeroconfServer__server') and hasattr(zs._ZeroconfServer__server, 'name'):
        device_name = zs._ZeroconfServer__server.name

    logging.info(f"Spotify Connect device '{Colors.CYAN}{device_name}{Colors.ENDC}' is now available on your network.")
    logging.info(f"Please open Spotify on another device, and {Colors.BOLD}transfer playback to it{Colors.ENDC}.")
    logging.info("This will capture your session and save it as 'credentials.json'.")

    try:
        while True:
            time.sleep(1)
            if credential_file.is_file() and credential_file.stat().st_size > 0:
                logging.info(f"'{Colors.GREEN}credentials.json{Colors.ENDC}' has been created.")
                if hasattr(zs, '_ZeroconfServer__session') and zs._ZeroconfServer__session:
                    try:
                        username = zs._ZeroconfServer__session.username()
                        logging.info(f"Session captured for user: {Colors.GREEN}{username}{Colors.ENDC}")
                    except Exception:
                        pass # It's ok if we can't get username
                break
    finally:
        logging.info("Shutting down Spotify Connect server...")
        zs.close()

def check_and_configure_api_creds(base_url):
    """
    Checks if Spotizerr has Spotify API credentials and prompts user to add them if missing.
    """
    api_config_url = f"{base_url.rstrip('/')}/api/credentials/spotify_api_config"
    logging.info("Checking Spotizerr server for Spotify API configuration...")

    try:
        response = requests.get(api_config_url, timeout=10)
        if response.status_code >= 400:
             response.raise_for_status()

        data = response.json()
        client_id = data.get("client_id")
        client_secret = data.get("client_secret")

        if client_id and client_secret:
            logging.info(f"{Colors.GREEN}Spotizerr API credentials are already configured.{Colors.ENDC}")
            return True

        logging.warning(f"{Colors.YELLOW}Spotizerr server is missing Spotify API credentials (client_id/client_secret).{Colors.ENDC}")
        logging.warning("You can get these from the Spotify Developer Dashboard: https://developer.spotify.com/dashboard")
        configure_now = input(f"Do you want to configure them now? ({Colors.GREEN}y{Colors.ENDC}/{Colors.BOLD}N{Colors.ENDC}): ").lower()

        if configure_now != 'y':
            logging.info("Please configure the API credentials on your Spotizerr server before proceeding.")
            return False

        new_client_id = input(f"Enter your Spotify {Colors.CYAN}client_id{Colors.ENDC}: ")
        new_client_secret = input(f"Enter your Spotify {Colors.CYAN}client_secret{Colors.ENDC}: ")

        if not new_client_id or not new_client_secret:
            logging.error(f"{Colors.RED}Both client_id and client_secret must be provided.{Colors.ENDC}")
            return False

        payload = {"client_id": new_client_id, "client_secret": new_client_secret}
        headers = {"Content-Type": "application/json"}

        put_response = requests.put(api_config_url, headers=headers, json=payload, timeout=10)
        put_response.raise_for_status()

        logging.info("Successfully configured Spotizerr API credentials.")
        return True

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to communicate with Spotizerr API at {api_config_url}: {e}")
        if e.response is not None:
            logging.error(f"Response status: {e.response.status_code}")
            try:
                logging.error(f"Response body: {e.response.json()}")
            except json.JSONDecodeError:
                logging.error(f"Response body: {e.response.text}")
        logging.error("Please ensure your Spotizerr instance is running and accessible at the specified URL.")
        return False

def main():
    """
    Main function for the Spotizerr auth utility.
    """
    try:
        base_url = input("Enter the base URL of your Spotizerr instance [default: http://localhost:7171]: ")
        if not base_url:
            base_url = "http://localhost:7171"
            logging.info(f"Using default base URL: {base_url}")

        if not base_url.startswith(('http://', 'https://')):
            base_url = 'http://' + base_url

        if not check_and_configure_api_creds(base_url):
            sys.exit(1)

        account_name = input("Enter a name for this Spotify account: ")
        if not account_name:
            logging.error("Account name cannot be empty.")
            sys.exit(1)

        region = input("Enter your Spotify region (e.g., US, DE, MX). This is the 2-letter country code: ").upper()
        if not region:
            logging.error("Region cannot be empty.")
            sys.exit(1)

        cred_file = pathlib.Path("credentials.json")
        if cred_file.exists():
            overwrite = input(f"'{cred_file}' already exists. Overwrite it by connecting to Spotify? (y/N): ").lower()
            if overwrite == 'y':
                get_spotify_session_and_wait_for_credentials()
            else:
                logging.info("Using existing 'credentials.json'.")
        else:
            get_spotify_session_and_wait_for_credentials()
        
        if not cred_file.exists():
            logging.error("Failed to obtain 'credentials.json'. Exiting.")
            sys.exit(1)

        try:
            with open(cred_file, "r") as f:
                credentials_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Could not read or parse 'credentials.json': {e}")
            sys.exit(1)

        payload = {
            "region": region,
            "blob_content": credentials_data
        }

        api_url = f"{base_url.rstrip('/')}/api/credentials/spotify/{account_name}"
        headers = {"Content-Type": "application/json"}

        logging.info(f"Registering account '{account_name}' to Spotizerr at '{api_url}'")

        try:
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
            logging.info("Successfully registered/updated Spotify account in Spotizerr!")
            if response.text:
                logging.info(f"Response from server: {response.text}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to call Spotizerr API: {e}")
            if e.response is not None:
                logging.error(f"Response status: {e.response.status_code}")
                logging.error(f"Response body: {e.response.text}")
            sys.exit(1)
        finally:
            cleanup = input("Do you want to delete 'credentials.json' now? (y/N): ").lower()
            if cleanup == 'y':
                try:
                    if cred_file.exists():
                        cred_file.unlink()
                        logging.info("'credentials.json' deleted.")
                except OSError as e:
                    logging.error(f"Error deleting 'credentials.json': {e}")
            else:
                logging.info("'credentials.json' not deleted.")

        sys.exit(0)

    except KeyboardInterrupt:
        logging.info("\nOperation cancelled by user. Exiting.")
        sys.exit(0)


if __name__ == "__main__":
    main()
