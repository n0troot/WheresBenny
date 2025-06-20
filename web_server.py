import os
import io
import json
import time
import uuid
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Directory for temporary image files
TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

# Store active games
active_games = {}
# Format: {
#   "game_id": {
#     "image_path": "path/to/image.png",
#     "expiry_time": timestamp,
#     "x_pos": x,
#     "y_pos": y,
#     "width": w,
#     "height": h,
#     "discord_channel_id": id,
#     "creator_user_id": id,
#     "finder_callback": callback_function,
#     "created_by": "username"
#   }
# }

# Server settings
HOST = "0.0.0.0"  # Listen on all interfaces to make it publicly accessible
PORT = 9090  # Updated port for Ubuntu server

# For server deployment
def get_public_url():
    """Get the public URL for server deployment"""
    # Use complete URL if specified (make sure it has protocol and port if needed)
    server_url = os.environ.get("SERVER_URL", "")
    if server_url:
        # Ensure protocol is included
        if not server_url.startswith(("http://", "https://")):
            server_url = f"http://{server_url}"
        
        # Add port if not already included and if not using https (443) or standard http (80)
        if ":" not in server_url.split("/")[-1] and not server_url.startswith("https"):
            server_url = f"{server_url}:{PORT}"
            
        return server_url.rstrip('/')
    
    # Use IP or hostname from environment if specified
    hostname = os.environ.get("SERVER_HOSTNAME", "")
    if hostname:
        # Ensure there's no protocol in the hostname
        if hostname.startswith(("http://", "https://")):
            hostname = hostname.split("//")[1]
        
        # Strip any existing port from hostname
        if ":" in hostname:
            hostname = hostname.split(":")[0]
            
        return f"http://{hostname}:{PORT}"
    
    # Check if running on Replit (as fallback)
    if "REPL_ID" in os.environ and "REPL_SLUG" in os.environ and "REPL_OWNER" in os.environ:
        return f"https://{os.environ['REPL_SLUG']}.{os.environ['REPL_OWNER']}.repl.co"
    
    # If we get here, log an error message and use localhost as last resort
    print("\n⚠️  WARNING: SERVER_HOSTNAME or SERVER_URL environment variable not set!")
    print("   Game URLs will not work correctly unless you specify your server's public IP or domain.")
    print("   Please set SERVER_HOSTNAME=129.159.156.225 or SERVER_URL=http://ownd.lol:9090 in your .env file.\n")
    
    # Default to 127.0.0.1 (localhost) instead of 0.0.0.0 as a last resort
    return f"http://127.0.0.1:{PORT}"

class WhereIsBennyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """Silence server logs for cleanliness"""
        return

    def do_GET(self):
        """Handle GET requests for game pages and images"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # Serve the game page
        if path.startswith("/game/"):
            game_id = path.split("/")[-1]
            if game_id in active_games:
                game = active_games[game_id]
                # Check if game has expired
                if time.time() > game["expiry_time"]:
                    self.send_error(404, "Game has expired")
                    remove_game(game_id)
                    return
                    
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                
                # Generate HTML with clickable image map
                html = generate_game_html(game_id, game)
                self.wfile.write(html.encode())
            else:
                self.send_error(404, "Game not found")
        
        # Serve image files
        elif path.startswith("/images/"):
            image_name = path.split("/")[-1]
            image_path = os.path.join(TEMP_DIR, image_name)
            
            if os.path.exists(image_path):
                self.send_response(200)
                if image_path.endswith(".png"):
                    self.send_header("Content-type", "image/png")
                else:
                    self.send_header("Content-type", "image/jpeg")
                self.end_headers()
                
                with open(image_path, "rb") as img_file:
                    self.wfile.write(img_file.read())
            else:
                self.send_error(404, "Image not found")
        
        # Handle found Benny clicks
        elif path.startswith("/found/"):
            query_components = parse_qs(parsed_url.query)
            game_id = path.split("/")[-1]
            finder_name = query_components.get("user", ["Unknown"])[0]
            
            if game_id in active_games:
                game = active_games[game_id]
                
                # Call the callback function to notify Discord
                if game["finder_callback"]:
                    game["finder_callback"](finder_name, game["discord_channel_id"], game["created_by"])
                
                # Return a success page
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                
                success_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Found Benny!</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }}
                        .success {{ color: green; font-size: 24px; }}
                    </style>
                </head>
                <body>
                    <h1 class="success">Congratulations, {finder_name}!</h1>
                    <p>You found Benny! The Discord channel has been notified.</p>
                    <p>You can close this window now.</p>
                </body>
                </html>
                """
                self.wfile.write(success_html.encode())
                
                # Remove the game after it's been found
                remove_game(game_id)
            else:
                self.send_error(404, "Game not found")
        else:
            self.send_error(404, "Not found")

def generate_game_html(game_id, game):
    """Generate HTML for the game page with clickable image map"""
    # Get the image dimensions for the map
    x, y = game["x_pos"], game["y_pos"]
    width, height = game["width"], game["height"]
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Where's Benny?</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
                text-align: center;
                touch-action: manipulation; /* Prevent double-tap zoom */
            }}
            .container {{
                max-width: 100%;
                margin: 0 auto;
                padding: 20px;
            }}
            h1 {{
                color: #333;
            }}
            .game-image {{
                position: relative;
                margin: 20px auto;
                max-width: 100%;
                cursor: crosshair;
                display: inline-block; /* Keep container tight to image */
                -webkit-tap-highlight-color: rgba(0,0,0,0); /* Remove tap highlight on iOS */
                touch-action: manipulation; /* Improve touch response */
            }}
            .game-image img {{
                max-width: 100%;
                height: auto;
                border: 2px solid #333;
                display: block; /* Remove extra space below image */
                -webkit-user-select: none; /* Prevent selection on iOS */
                user-select: none; /* Standard syntax */
                -webkit-touch-callout: none; /* Disable callout */
            }}
            /* Benny target indicator - only visible in debug mode */
            .benny-target-debug {{
                position: absolute;
                border: 2px dashed red;
                background-color: rgba(255,0,0,0.3);
                pointer-events: none;
                z-index: 100;
                display: none; /* Hidden by default */
            }}
            /* Style to prevent visible cursor change over clickable area */
            area {{
                cursor: inherit !important;
            }}
            /* For debug mode only - uncomment to see Benny's hitbox */
            /*
            .debug-hitbox {{
                position: absolute;
                border: 2px solid red;
                background-color: rgba(255,0,0,0.3);
                pointer-events: none;
                z-index: 100;
            }}
            */
            .timer {{
                margin-top: 20px;
                font-size: 18px;
                color: #555;
            }}
            .instructions {{
                margin-bottom: 20px;
                color: #555;
            }}
            /* Modal popup styles */
            .modal {{
                display: none;
                position: fixed;
                z-index: 100;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.7);
                align-items: center;
                justify-content: center;
            }}
            .modal-content {{
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                max-width: 500px;
                width: 80%;
                text-align: center;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            }}
            input {{
                display: block;
                margin: 20px auto;
                padding: 10px;
                width: 80%;
                font-size: 16px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }}
            button {{
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                font-size: 16px;
                cursor: pointer;
                transition: background-color 0.3s;
            }}
            button:hover {{
                background-color: #45a049;
            }}
            h2 {{
                color: #333;
                margin-top: 0;
            }}
            .benny-hotspot {{
                cursor: inherit !important;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Where's Benny?</h1>
            <div class="instructions">Find and click on Benny in the image below!</div>
            
            <div class="game-image" id="gameImageContainer">
                <img src="/images/{game_id}.png" id="gameImage" alt="Where's Benny?">
                <!-- We'll handle click detection in JavaScript for faster mobile response -->
                <!-- Benny's position is at: x={x}, y={y}, w={width}, h={height} -->
            </div>
            
            <div class="timer">Game expires in <span id="countdown">5:00</span></div>
        </div>
        
        <!-- Name input modal popup -->
        <div id="nameModal" class="modal">
            <div class="modal-content">
                <h2>You found Benny!</h2>
                <p>Enter your name to claim victory:</p>
                <input type="text" id="username-input" placeholder="Your name" autofocus>
                <button onclick="submitName()">Submit</button>
            </div>
        </div>
        
        <script>
            // Store Benny's position and game data
            const bennyData = {{
                x: {x},
                y: {y},
                width: {width},
                height: {height},
                padding: 15  // Extra padding to make it easier to tap
            }};
            
            // Setup countdown timer
            let timeLeft = {int(game["expiry_time"] - time.time())};
            const countdownEl = document.getElementById('countdown');
            const nameModal = document.getElementById('nameModal');
            
            // Simple timer function
            function updateTimer() {{
                if (timeLeft <= 0) {{
                    window.location.href = "/"; // Game expired
                    return;
                }}
                
                const minutes = Math.floor(timeLeft / 60);
                const seconds = timeLeft % 60;
                countdownEl.textContent = `${{minutes}}:${{seconds.toString().padStart(2, '0')}}`;
                timeLeft--;
                setTimeout(updateTimer, 1000);
            }}
            
            // Start the timer
            updateTimer();
            
            // Fast mobile touch handling (no delay)
            function setupFastTouchHandling() {{
                const container = document.getElementById('gameImageContainer');
                const img = document.getElementById('gameImage');
                
                if (!container || !img) return;
                
                // Pre-calculate values once for better performance
                let imgWidth, imgHeight, scaleX, scaleY;
                
                function updateDimensions() {{
                    // Get current display dimensions
                    imgWidth = img.clientWidth;
                    imgHeight = img.clientHeight;
                    
                    // Calculate scale ratio
                    scaleX = imgWidth / img.naturalWidth;
                    scaleY = imgHeight / img.naturalHeight;
                    
                    // DEBUG: Uncomment to show Benny's location
                    // showDebugOverlay();
                }}
                
                // Optional: Show debug overlay to see where Benny is located
                function showDebugOverlay() {{
                    let overlay = document.querySelector('.benny-target-debug');
                    if (!overlay) {{
                        overlay = document.createElement('div');
                        overlay.className = 'benny-target-debug';
                        container.appendChild(overlay);
                    }}
                    
                    // Position the overlay at Benny's location
                    const scaledX = bennyData.x * scaleX;
                    const scaledY = bennyData.y * scaleY;
                    const scaledWidth = bennyData.width * scaleX;
                    const scaledHeight = bennyData.height * scaleY;
                    
                    overlay.style.left = scaledX + 'px';
                    overlay.style.top = scaledY + 'px';
                    overlay.style.width = scaledWidth + 'px';
                    overlay.style.height = scaledHeight + 'px';
                    overlay.style.display = 'block';
                }}
                
                // Handle click/tap events with maximum efficiency
                function handleInteraction(event) {{
                    // Get interaction coordinates
                    let x, y;
                    
                    // Touch event
                    if (event.touches && event.touches.length > 0) {{
                        const rect = img.getBoundingClientRect();
                        x = event.touches[0].clientX - rect.left;
                        y = event.touches[0].clientY - rect.top;
                        event.preventDefault(); // Prevent scrolling/zooming
                    }} 
                    // Mouse event
                    else {{
                        const rect = img.getBoundingClientRect();
                        x = event.clientX - rect.left;
                        y = event.clientY - rect.top;
                    }}
                    
                    // Calculate scaled position of Benny
                    const scaledX = bennyData.x * scaleX;
                    const scaledY = bennyData.y * scaleY;
                    const scaledWidth = bennyData.width * scaleX;
                    const scaledHeight = bennyData.height * scaleY;
                    const padding = bennyData.padding * scaleX; // Scale padding too
                    
                    // Check if click/tap is on Benny
                    if (x >= (scaledX - padding) && 
                        x <= (scaledX + scaledWidth + padding) && 
                        y >= (scaledY - padding) && 
                        y <= (scaledY + scaledHeight + padding)) {{
                        foundBenny();
                        return false;
                    }}
                }}
                
                // Add all event listeners with the right flags for performance
                img.addEventListener('click', handleInteraction, false);
                img.addEventListener('touchstart', handleInteraction, {{passive: false}});
                
                // Handle resize to keep coordinates correct
                window.addEventListener('resize', updateDimensions);
                
                // Initialize dimensions
                img.onload = updateDimensions;
                // If image might already be loaded
                if (img.complete) {{
                    updateDimensions();
                }}
            }}
            
            // When Benny is found, show the name input modal
            function foundBenny() {{
                // Show modal immediately (better response time)
                nameModal.style.display = 'flex';
                
                // Focus the input field (slight delay to ensure modal is visible first)
                setTimeout(function() {{
                    document.getElementById('username-input').focus();
                }}, 10);
                
                // Allow Enter key to submit
                document.getElementById('username-input').addEventListener('keyup', function(event) {{
                    if (event.key === 'Enter') {{
                        submitName();
                    }}
                }});
            }}
            
            // Submit name and redirect
            function submitName() {{
                const name = document.getElementById('username-input').value || 'Anonymous';
                window.location.href = `/found/{game_id}?user=${{encodeURIComponent(name)}}`;
            }}
            
            // Initialize everything when page loads
            window.addEventListener('DOMContentLoaded', function() {{
                setupFastTouchHandling();
            }});
            
        </script>
    </body>
    </html>
    """
    return html

def start_server():
    """Start the HTTP server in a separate thread"""
    server = HTTPServer((HOST, PORT), WhereIsBennyHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    print(f"Started HTTP server at http://{HOST}:{PORT}")
    return server

def stop_server(server):
    """Stop the HTTP server"""
    server.shutdown()
    server.server_close()
    print("Stopped HTTP server")

def create_game(image, x_pos, y_pos, width, height, discord_channel_id, creator_id, creator_name, finder_callback):
    """Create a new game and return its ID and URL"""
    # Generate a unique ID for this game
    game_id = str(uuid.uuid4()).replace("-", "")[:12]
    
    # Save the image to a file
    image_path = os.path.join(TEMP_DIR, f"{game_id}.png")
    image.save(image_path, "PNG")
    
    # Create game entry with 5-minute expiry
    active_games[game_id] = {
        "image_path": image_path,
        "expiry_time": time.time() + 300,  # 5 minutes
        "x_pos": x_pos,
        "y_pos": y_pos,
        "width": width,
        "height": height,
        "discord_channel_id": discord_channel_id,
        "creator_user_id": creator_id,
        "finder_callback": finder_callback,
        "created_by": creator_name
    }
    
    # Create the game URL using the public URL from Replit if available
    base_url = get_public_url()
    game_url = f"{base_url}/game/{game_id}"
    
    return game_id, game_url

def remove_game(game_id):
    """Remove a game and its resources"""
    if game_id in active_games:
        # Delete the image file
        image_path = active_games[game_id]["image_path"]
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            print(f"Error removing game file: {e}")
        
        # Remove from active games
        del active_games[game_id]

def cleanup_expired_games():
    """Remove expired games"""
    now = time.time()
    expired_games = [game_id for game_id, game in active_games.items() if now > game["expiry_time"]]
    
    for game_id in expired_games:
        remove_game(game_id)

# Start automatic cleanup in a background thread
def start_cleanup_thread():
    def cleanup_task():
        while True:
            cleanup_expired_games()
            time.sleep(60)  # Check every minute
    
    cleanup_thread = threading.Thread(target=cleanup_task)
    cleanup_thread.daemon = True
    cleanup_thread.start()

# Server instance
server_instance = None

def initialize():
    """Initialize the web server"""
    global server_instance
    # Create temp directory if it doesn't exist
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Start the server
    server_instance = start_server()
    
    # Start cleanup thread
    start_cleanup_thread()
    
    return server_instance

if __name__ == "__main__":
    # Test the server
    initialize()
    input("Press Enter to stop server...")
    if server_instance:
        stop_server(server_instance)
