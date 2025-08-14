# Spotizerr Authentication Utility

A command-line tool to help you authenticate and register a Spotify account with your Spotizerr instance. This utility simplifies the process by programmatically capturing Spotify session credentials and posting them to your Spotizerr backend.

## Features

-   **Interactive Setup**: Guides you through the process of connecting to your Spotizerr instance.
-   **API Credential Check**: Automatically checks if your Spotizerr instance has the required Spotify API `client_id` and `client_secret` and prompts you to add them if they are missing.
-   **Spotify Connect Integration**: Uses `librespot-spotizerr` to create a temporary Spotify Connect device, allowing you to capture credentials securely by simply playing a song.
-   **Colored Output**: Uses color-coded terminal output to highlight important information and make the process easier to follow.
-   **Clean Exit**: Gracefully handles interruptions and ensures a clean shutdown.

## Prerequisites

-   Docker
-   A running instance of [Spotizerr](https://github.com/Xoconoch/spotizerr).
-   Spotify `client_id` and `client_secret`. You can get these by creating an application on the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).

## Usage

Run the script from your terminal:

```bash
docker run --network=host --rm -it cooldockerizer93/spotizerr-auth
```

The script will guide you through the following steps:

1.  **Enter Spotizerr URL**: You'll be prompted for the base URL of your Spotizerr instance. You can press Enter to use the default (`http://localhost:7171`).

2.  **Configure API Credentials**: The script checks if your Spotizerr instance is configured with a Spotify `client_id` and `client_secret`.
    -   If they are missing, it will ask if you want to configure them.
    -   Select `y` and enter your credentials when prompted. This is a one-time setup.

3.  **Enter Account Details**:
    -   Provide a **name for the account** to identify it in Spotizerr.
    -   Enter your two-letter **Spotify region code** (e.g., `US`, `DE`, `MX`).

4.  **Authenticate via Spotify Connect**:
    -   The utility will start a Spotify Connect device on your network (e.g., `librespot-spotizerr`).
    -   Open Spotify on any device (phone, desktop), start playing a track, and use the "Connect to a device" feature to **transfer playback to the new device**.
    -   Once you transfer playback, the script captures the session, creates a `credentials.json` file, and shuts down the Connect server.

5.  **Register with Spotizerr**: The script automatically sends the captured credentials to your Spotizerr instance, creating or updating the account.

6.  **Cleanup**: Finally, it will ask if you want to delete the `credentials.json` file. It's recommended to do so for security.

After these steps, your Spotify account will be registered in Spotizerr and ready to use.

## How It Works

The script uses `librespot-spotizerr`'s Zeroconf implementation to advertise a Spotify Connect device on the local network. When you transfer playback to this device, `librespot-spotizerr` handles the authentication with Spotify's servers and stores the session details (including the necessary refresh token) in a local `credentials.json` file.

Once this file is created, the script reads it and makes a `POST` request to the Spotizerr API endpoint `/api/credentials/spotify/{accountName}`. The request body is a JSON object containing the user's region and the contents of `credentials.json`, which Spotizerr then stores for future use.

The initial check for `client_id` and `client_secret` ensures that Spotizerr has the necessary global API credentials to perform metadata lookups and other API-dependent tasks. 
