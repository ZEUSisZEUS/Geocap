GeoCap Proxy Framework

A powerful Flask-based web proxy framework for proxying websites, collecting detailed client information, and triggering interactive client-side actions like geolocation, webcam snapshots, and custom popups. The framework includes a real-time CLI for controlling connected clients and supports both local and global (Cloudflared) access modes.
Features

Website Proxying: Proxy websites (e.g., Discord, YouTube) through your server, injecting custom JavaScript to enhance functionality.
Client Information Collection: Gather detailed device info, including:
Browser, OS, and device type (mobile, tablet, desktop).
Screen resolution, timezone, and hardware details.
IP address, geolocation, and ISP information (with optional GeoIP database).
Battery status, network info, and WebGL details.


Interactive Client Actions:
Trigger geolocation requests with themed popups (customized for sites like Gmail, Discord).
Capture webcam snapshots (up to 3 per request) and save them as PNG files.
Initiate file downloads or display custom popup messages.
Redirect clients to other URLs.


Real-Time CLI: Control connected clients via an interactive command-line interface with commands like location, camera, proxy, and redirect.
Local and Global Modes: Run locally or expose the server globally using Cloudflared tunnels.
Themed Popups: Customize popups to match the proxied website’s branding (e.g., Gmail’s blue theme).
Weather Integration: Fetch weather data for clients’ GPS coordinates using Open-Meteo API.

Screenshots

Prerequisites

Python 3.8+
Dependencies:
flask
flask-socketio
requests
beautifulsoup4
colorama
geoip2 (optional, for enhanced IP geolocation)
cloudflared (optional, for global access)


GeoLite2-City.mmdb database (optional, for IP geolocation)
A modern web browser for testing

Setup Instructions

Clone the Repository (or save the script as geocap.py):
git clone <repository-url>
cd geocap


Install Dependencies:
pip install flask flask-socketio requests beautifulsoup4 colorama geoip2


Optional: Set Up GeoIP Database:

Download the GeoLite2-City database from MaxMind.
Place GeoLite2-City.mmdb in the project directory.
Note: Without this, IP geolocation will rely on external APIs (ipapi.co, ipinfo.io).


Optional: Install Cloudflared for Global Access:

Install Cloudflared: Cloudflared Installation Guide.
Ensure cloudflared is in your system PATH.


Run the Script:
python geocap.py

The server starts on http://localhost:5000, and the CLI interface appears in the terminal.


Usage

Start the Server:

Run python geocap.py to launch the Flask server and CLI.
The CLI displays connected clients and available commands.


Access the Proxy:

Local Mode: Open http://<your-local-ip>:5000 in a browser (e.g., http://192.168.1.100:5000).
Global Mode: Use the CLI command mode to switch to global mode, which starts a Cloudflared tunnel and provides a public URL (e.g., https://<random>.trycloudflare.com).


Proxy a Website:

In the CLI, type proxy and select a site (e.g., 1 for Discord) or enter a custom URL (e.g., https://gmail.com).
Access the proxy URL (e.g., http://localhost:5000/proxy?url=https://gmail.com).
Note: Proxying Google services (e.g., Gmail) may fail due to security restrictions or redirects. Test with simpler sites like https://example.com first.


CLI Commands:

location: Trigger a geolocation popup for a client (e.g., “Gmail requires location verification”).
camera: Request webcam access and capture 3 snapshots, saved as PNG files.
download: Initiate a file download for a client (specify a local file path).
message: Display a custom popup with a title, message, and colors.
info: Collect and display detailed client device information.
redirect: Redirect a client to another URL (e.g., a proxied site).
mode: Switch between local and global (Cloudflared) modes.
weather: Fetch weather data for a client’s GPS coordinates (requires prior location command).
quit: Shut down the server.

Example:
➤ proxy
Select a website to proxy:
  1. https://discord.com
  2. https://instagram.com
  ...
  9. Custom URL
> 9
Enter URL to proxy (include https://): https://example.com
🔗 Proxy URL ready: http://192.168.1.100:5000/proxy?url=https://example.com
Open in browser? (y/n): y


View Client Data:

Device info is saved to device_info_<client-ip>.json.
Webcam snapshots are saved as snapshot_<client-ip>_<count>_<timestamp>.png.
Logs in the CLI show real-time client activity (e.g., connections, geolocation, snapshots).



Limitations

Google Services (e.g., Gmail): Google’s security measures (e.g., redirects to https://accounts.google.com, CORS restrictions) may prevent proper proxying. The script injects JavaScript, but Gmail’s JavaScript-heavy interface and authentication can cause redirects or styling issues. Test with static sites like https://example.com for better results.
Cloudflared: Requires a working cloudflared installation for global mode. Ensure it’s in your PATH.
GeoIP Database: Without GeoLite2-City.mmdb, geolocation relies on less accurate external APIs.
JavaScript-Dependent Sites: Complex sites may break due to absolute URLs or client-side redirects not fully rewritten.

Ethical and Legal Considerations

User Consent: Collecting device information, geolocation, or webcam snapshots requires explicit user consent. Ensure users are informed of data collection via clear popups (included in the script).
Privacy Laws: Comply with local regulations (e.g., GDPR, CCPA) when handling personal data like IP addresses or geolocation.
Responsible Use: Use this tool for educational purposes or with permission. Unauthorized data collection or proxying may violate terms of service or laws.

Troubleshooting

404 Error for /proxy: Ensure you’re accessing the correct URL (e.g., http://localhost:5000/proxy?url=https://example.com). If behind a reverse proxy (e.g., Nginx), configure it to forward /proxy to the Flask app.
Redirects to Original Site: Check CLI logs for 301/302 status codes or Location headers. The script rewrites URLs, but complex sites like Gmail may require additional handling.
Camera/Geolocation Denied: Users may deny permissions, which the script logs. Ensure popups are clear and themed appropriately.
Cloudflared Fails: Verify cloudflared is installed and accessible in your PATH.

Contributing
Contributions are welcome! Fork the repository, make changes, and submit a pull request. Report issues or suggest features via the issue tracker.
License
This project is licensed under the MIT License. See the LICENSE file for details.
