import os
import io
import random
import discord
from discord.ext import commands
import requests
from PIL import Image
import time
from dotenv import load_dotenv

# Import the web server module
import web_server

# Load environment variables
load_dotenv()

# Set up Discord bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Path to Benny image
BENNY_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "benny.png")

# Hugging Face API endpoint for image generation
HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

# Headers for Hugging Face API
headers = {
    "Authorization": f"Bearer {HUGGINGFACE_API_KEY}"
}

# Track last image generation to prevent spam
# Format: {user_id: timestamp}
last_generated = {}

# Global variable to track if we're currently generating an image
# This prevents simultaneous generations
generating_image = False

# Load backgrounds for where's Waldo style images from file
def load_prompts_from_file():
    prompts = []
    try:
        # Try to load prompts from the text file
        prompt_file = os.path.join(os.path.dirname(__file__), "waldo_prompts.txt")
        if os.path.exists(prompt_file):
            with open(prompt_file, "r") as f:
                for line in f:
                    # Skip empty lines and comments
                    line = line.strip()
                    if line and not line.startswith("#"):
                        prompts.append(line)
            print(f"Loaded {len(prompts)} background prompts from file")
        else:
            print("Prompt file not found, using default prompts")
    except Exception as e:
        print(f"Error loading prompts: {e}")

    # If no prompts were loaded (or there was an error), use these defaults
    if not prompts:
        prompts = [
            "a crowded beach scene in the style of Where's Waldo, very detailed with hundreds of tiny people",
            "a bustling city street with hundreds of people in the style of Where's Waldo, colorful and detailed illustration",
            "a packed amusement park with rides and crowds in the style of Where's Waldo, very detailed cartoon style",
            "a busy shopping mall with many shoppers in the style of Where's Waldo, detailed illustration",
            "a crowded rock concert with thousands of fans in the style of Where's Waldo, detailed illustration",
            "a large sporting event stadium filled with spectators in the style of Where's Waldo, detailed illustration",
            "a busy airport terminal with travelers in the style of Where's Waldo, detailed cartoon style",
            "a crowded train station with commuters in the style of Where's Waldo, detailed cartoon style"
        ]
        print(f"Using {len(prompts)} default prompts")

    return prompts

# Load the prompts
BACKGROUND_PROMPTS = [
    "a crowded beach scene in the style of Where's Waldo, very detailed with hundreds of tiny people",
    "a bustling city street with hundreds of people in the style of Where's Waldo, colorful and detailed illustration",
    "a packed amusement park with rides and crowds in the style of Where's Waldo, very detailed cartoon style",
    "a busy shopping mall with many shoppers in the style of Where's Waldo, detailed illustration",
    "a crowded rock concert with thousands of fans in the style of Where's Waldo, detailed illustration",
    "a large sporting event stadium filled with spectators in the style of Where's Waldo, detailed illustration",
    "a busy airport terminal with travelers in the style of Where's Waldo, detailed cartoon style",
    "a crowded train station with commuters in the style of Where's Waldo, detailed cartoon style",
    "a medieval castle festival with hundreds of visitors in the style of Where's Waldo, detailed illustration",
    "a bustling farmer's market with vendors and shoppers in the style of Where's Waldo, colorful detailed scene",
    "a crowded public swimming pool in summer in the style of Where's Waldo, detailed cartoon style",
    "a huge comic convention with cosplayers in the style of Where's Waldo, vibrant detailed illustration",
    "a busy ski resort with skiers and snowboarders in the style of Where's Waldo, detailed winter scene",
    "a massive library with many readers and bookshelves in the style of Where's Waldo, detailed illustration",
    "a carnival with rides and games in the style of Where's Waldo, colorful detailed cartoon style",
    "a crowded museum with art viewers in the style of Where's Waldo, detailed illustration",
    "a busy restaurant with many diners and waitstaff in the style of Where's Waldo, detailed scene",
    "a public park on a sunny day with many visitors in the style of Where's Waldo, detailed illustration",
    "a university campus during class change in the style of Where's Waldo, detailed scene with students",
    "a massive grocery store with shoppers in the style of Where's Waldo, detailed illustration",
    "a crowded movie theater lobby with moviegoers in the style of Where's Waldo, detailed scene",
    "a busy hospital waiting room in the style of Where's Waldo, detailed illustration",
    "a packed water park with swimmers and slides in the style of Where's Waldo, colorful detailed scene",
    "a giant cruise ship deck with passengers in the style of Where's Waldo, detailed vacation scene",
    "a tech conference exhibit hall with attendees in the style of Where's Waldo, detailed illustration",
    "a crowded zoo with visitors viewing animals in the style of Where's Waldo, detailed nature scene",
    "a busy arcade with gamers playing at machines in the style of Where's Waldo, colorful detailed scene",
    "a crowded botanical garden with visitors in the style of Where's Waldo, detailed nature illustration",
    "a school playground during recess in the style of Where's Waldo, detailed children's scene",
    "a massive outdoor music festival with multiple stages in the style of Where's Waldo, detailed illustration",
    "a crowded courthouse with lawyers and visitors in the style of Where's Waldo, detailed scene",
    "a luxury hotel lobby with travelers and staff in the style of Where's Waldo, detailed illustration",
    "a crowded bowling alley on league night in the style of Where's Waldo, detailed scene",
    "a busy nightclub with dancers and partygoers in the style of Where's Waldo, colorful detailed illustration",
    "a packed gym with people working out in the style of Where's Waldo, detailed fitness scene",
    "a crowded aquarium with visitors viewing sea life in the style of Where's Waldo, detailed underwater theme",
    "a busy bakery with customers and bakers in the style of Where's Waldo, detailed food scene",
    "a large outdoor flea market with vendors and shoppers in the style of Where's Waldo, detailed illustration",
    "a crowded ice skating rink with skaters in the style of Where's Waldo, detailed winter scene",
    "a massive construction site with workers in the style of Where's Waldo, detailed illustration",
    "a busy salon with hairstylists and clients in the style of Where's Waldo, detailed scene",
    "a crowded dog park with pet owners and dogs in the style of Where's Waldo, detailed illustration",
    "a busy laundromat with people doing laundry in the style of Where's Waldo, detailed scene",
    "a large college graduation ceremony in the style of Where's Waldo, detailed academic scene",
    "a crowded public beach boardwalk with tourists in the style of Where's Waldo, detailed coastal scene",
    "a busy traffic intersection in a major city in the style of Where's Waldo, detailed urban illustration",
    "a packed church service with worshippers in the style of Where's Waldo, detailed religious scene",
    "a crowded dance studio with dancers in the style of Where's Waldo, detailed illustration",
    "a busy pet store with shoppers and animals in the style of Where's Waldo, detailed scene",
    "a large outdoor garden center with shoppers in the style of Where's Waldo, detailed plant illustration",
    "a crowded fishing pier with anglers in the style of Where's Waldo, detailed coastal scene",
    "a busy coffee shop with customers and baristas in the style of Where's Waldo, detailed illustration",
    "a crowded public swimming beach with sunbathers in the style of Where's Waldo, detailed summer scene",
    "a packed casino floor with gamblers in the style of Where's Waldo, colorful detailed illustration",
    "a busy comic book store with shoppers in the style of Where's Waldo, detailed geek culture scene",
    "a crowded vintage record store with music fans in the style of Where's Waldo, detailed retro illustration",
    "a large outdoor car show with enthusiasts in the style of Where's Waldo, detailed automotive scene",
    "a busy art supply store with shoppers in the style of Where's Waldo, colorful detailed illustration",
    "a crowded roller skating rink with skaters in the style of Where's Waldo, detailed retro scene",
    "a packed science museum with visitors in the style of Where's Waldo, detailed educational illustration",
    "a busy woodworking shop with craftspeople in the style of Where's Waldo, detailed scene",
    "a crowded farmers market with shoppers in the style of Where's Waldo, detailed food illustration",
    "a large bookstore with readers and browsers in the style of Where's Waldo, detailed literary scene",
    "a busy chess tournament with players in the style of Where's Waldo, detailed competitive illustration",
    "a crowded horse racing track with spectators in the style of Where's Waldo, detailed sporting scene",
    "a packed swimming competition with athletes and audience in the style of Where's Waldo, detailed illustration",
    "a busy hiking trail in a national park in the style of Where's Waldo, detailed nature scene",
    "a crowded food festival with vendors and eaters in the style of Where's Waldo, detailed culinary illustration",
    "a large classroom during an exam in the style of Where's Waldo, detailed academic scene",
    "a busy video gaming tournament with players in the style of Where's Waldo, detailed esports illustration",
    "a crowded outdoor yoga class in a park in the style of Where's Waldo, detailed fitness scene",
    "a packed indoor pool with swimmers in the style of Where's Waldo, detailed aquatic illustration",
    "a busy auto repair shop with mechanics in the style of Where's Waldo, detailed scene",
    "a crowded outdoor wedding with guests in the style of Where's Waldo, detailed celebration illustration",
    "a large art gallery opening with patrons in the style of Where's Waldo, detailed cultural scene",
    "a busy skateboard park with skateboarders in the style of Where's Waldo, detailed action illustration",
    "a crowded post office during the holidays in the style of Where's Waldo, detailed seasonal scene",
    "a packed children's playground with families in the style of Where's Waldo, detailed illustration",
    "a busy hardware store with shoppers in the style of Where's Waldo, detailed DIY scene",
    "a crowded outdoor basketball tournament in the style of Where's Waldo, detailed sporting illustration",
    "a large hot air balloon festival with spectators in the style of Where's Waldo, detailed colorful scene",
    "a busy tattoo convention with artists and attendees in the style of Where's Waldo, detailed illustration",
    "a crowded safari tour with tourists in the style of Where's Waldo, detailed wildlife scene",
    "a packed outdoor concert in a park in the style of Where's Waldo, detailed music illustration",
    "a busy antique store with browsers in the style of Where's Waldo, detailed vintage scene",
    "a crowded miniature golf course with players in the style of Where's Waldo, detailed recreational illustration",
    "a large renaissance faire with costumed attendees in the style of Where's Waldo, detailed historical scene",
    "a busy arcade bar with gamers in the style of Where's Waldo, detailed nostalgic illustration",
    "a crowded fishing tournament with participants in the style of Where's Waldo, detailed outdoor scene",
    "a packed food court in a mall in the style of Where's Waldo, detailed dining illustration",
    "a busy paint and sip art class in the style of Where's Waldo, detailed creative scene",
    "a crowded community pool on a hot day in the style of Where's Waldo, detailed summer illustration",
    "a large craft fair with vendors and shoppers in the style of Where's Waldo, detailed artisan scene",
    "a busy dog show with handlers and spectators in the style of Where's Waldo, detailed canine illustration",
    "a crowded bike race with cyclists and spectators in the style of Where's Waldo, detailed sporting scene",
    "a packed outdoor food truck festival in the style of Where's Waldo, detailed culinary illustration",
    "a busy pottery studio with artists in the style of Where's Waldo, detailed creative scene",
    "a crowded ballet performance with dancers and audience in the style of Where's Waldo, detailed cultural illustration",
    "a large outdoor yoga festival with participants in the style of Where's Waldo, detailed wellness scene",
    "a busy martial arts tournament with competitors in the style of Where's Waldo, detailed action illustration",
    "a crowded Halloween costume party in the style of Where's Waldo, detailed holiday scene",
    "a packed winter holiday market with shoppers in the style of Where's Waldo, detailed seasonal illustration",
    "a busy agricultural fair with visitors in the style of Where's Waldo, detailed rural scene",
    "a crowded outdoor ice hockey game with players and fans in the style of Where's Waldo, detailed winter illustration",
    "a large butterfly garden with visitors in the style of Where's Waldo, detailed nature scene",
    "a medieval jousting tournament with spectators in the style of Where's Waldo, detailed historical illustration",
    "a crowded water park wave pool with swimmers in the style of Where's Waldo, detailed summer scene",
    "a busy state fair midway with carnival games in the style of Where's Waldo, detailed festive illustration",
    "a crowded high school football game with fans in the style of Where's Waldo, detailed sporting scene",
    "a packed Broadway theater before showtime in the style of Where's Waldo, detailed cultural illustration",
    "a busy outdoor adventure park with zipliners in the style of Where's Waldo, detailed action scene",
    "a crowded apple orchard during picking season in the style of Where's Waldo, detailed autumn illustration",
    "a large cooking class with students in the style of Where's Waldo, detailed culinary scene",
    "a busy trampoline park with jumpers in the style of Where's Waldo, detailed action illustration",
    "a crowded drive-in movie theater with cars and viewers in the style of Where's Waldo, detailed nostalgic scene",
    "a packed board game cafe with players in the style of Where's Waldo, detailed recreational illustration",
    "a busy outdoor swimming competition with athletes in the style of Where's Waldo, detailed sporting scene",
    "a crowded laser tag arena with players in the style of Where's Waldo, detailed action illustration",
    "a large outdoor music festival campground in the style of Where's Waldo, detailed leisure scene",
    "a busy mountain ski lodge with visitors in the style of Where's Waldo, detailed winter illustration",
    "a crowded outdoor art installation with viewers in the style of Where's Waldo, detailed cultural scene",
    "a packed karaoke bar with singers and audience in the style of Where's Waldo, detailed entertainment illustration",
    "a busy escape room facility with participants in the style of Where's Waldo, detailed puzzle scene",
    "a crowded miniature train exhibit with viewers in the style of Where's Waldo, detailed hobby illustration",
    "a large botanical conservatory with visitors in the style of Where's Waldo, detailed nature scene",
    "a busy retro video game tournament in the style of Where's Waldo, detailed nostalgic illustration",
    "a crowded diner during breakfast rush in the style of Where's Waldo, detailed Americana scene",
    "a packed climbing gym with rock climbers in the style of Where's Waldo, detailed action illustration",
    "a busy community garden with gardeners in the style of Where's Waldo, detailed outdoor scene",
    "a crowded pinball arcade with players in the style of Where's Waldo, detailed nostalgic illustration",
    "a large outdoor movie screening in a park in the style of Where's Waldo, detailed entertainment scene",
    "a busy roller derby match with skaters and fans in the style of Where's Waldo, detailed action illustration",
    "a crowded flower show with visitors in the style of Where's Waldo, detailed botanical scene",
    "a packed science fiction convention with cosplayers in the style of Where's Waldo, detailed fan illustration",
    "a busy historical reenactment with participants in the style of Where's Waldo, detailed period scene",
    "a crowded virtual reality arcade with gamers in the style of Where's Waldo, detailed technology illustration",
    "a large indoor go-kart track with racers in the style of Where's Waldo, detailed action scene",
    "a busy outdoor street performance with audience in the style of Where's Waldo, detailed entertainment illustration",
    "a crowded magic show with audience members in the style of Where's Waldo, detailed performance scene",
    "a packed bounce house playground with children in the style of Where's Waldo, detailed fun illustration",
    "a busy farmers' cooperative with workers in the style of Where's Waldo, detailed agricultural scene",
    "a crowded indoor trampoline park with jumpers in the style of Where's Waldo, detailed action illustration",
    "a large outdoor boot camp fitness class in the style of Where's Waldo, detailed exercise scene",
    "a busy outdoor paintball field with players in the style of Where's Waldo, detailed action illustration",
    "a crowded outdoor archaeological dig with researchers in the style of Where's Waldo, detailed scientific scene",
    "a packed children's museum with families in the style of Where's Waldo, detailed educational illustration",
    "a busy taxidermy workshop with artisans in the style of Where's Waldo, detailed craft scene",
    "a crowded outdoor stargazing event with astronomers in the style of Where's Waldo, detailed scientific illustration",
    "a large kite festival on a beach in the style of Where's Waldo, detailed colorful scene",
    "a busy outdoor rock climbing wall with climbers in the style of Where's Waldo, detailed action illustration",
    "a crowded underwater hotel lobby in the style of Where's Waldo, detailed futuristic scene",
    "a packed dinosaur museum with visitors in the style of Where's Waldo, detailed prehistoric illustration",
    "a busy vintage car restoration shop in the style of Where's Waldo, detailed automotive scene",
    "a crowded county fair with rides and games in the style of Where's Waldo, detailed festival illustration",
    "a large outdoor dog agility competition in the style of Where's Waldo, detailed canine scene",
    "a busy medieval village market recreation in the style of Where's Waldo, detailed historical illustration",
    "a crowded outdoor classical music concert in the style of Where's Waldo, detailed cultural scene",
    "a packed arcade during a vintage pinball tournament in the style of Where's Waldo, detailed gaming illustration",
    "a busy chili cookoff with cooks and tasters in the style of Where's Waldo, detailed culinary scene",
    "a crowded outdoor drone racing competition in the style of Where's Waldo, detailed technology illustration",
    "a large technology repair shop with technicians in the style of Where's Waldo, detailed workplace scene",
    "a busy flower market with shoppers in the style of Where's Waldo, detailed botanical illustration",
    "a crowded insect museum with visitors in the style of Where's Waldo, detailed scientific scene",
    "a packed outdoor fishing competition with anglers in the style of Where's Waldo, detailed sporting illustration",
    "a busy holiday parade with spectators in the style of Where's Waldo, detailed celebration scene",
    "a crowded outdoor sculpture garden with art lovers in the style of Where's Waldo, detailed cultural illustration",
    "a large outdoor photography workshop with photographers in the style of Where's Waldo, detailed creative scene",
    "a busy model train exhibit with enthusiasts in the style of Where's Waldo, detailed hobby illustration",
    "a crowded scuba diving boat with divers in the style of Where's Waldo, detailed underwater scene",
    "a packed cryptocurrency conference with attendees in the style of Where's Waldo, detailed technology illustration",
    "a busy beekeeping workshop with apiarists in the style of Where's Waldo, detailed nature scene",
    "a crowded outdoor fencing competition with athletes in the style of Where's Waldo, detailed sporting illustration",
    "a large outdoor corporate team-building event in the style of Where's Waldo, detailed workplace scene",
    "a busy emergency room with medical staff in the style of Where's Waldo, detailed healthcare illustration",
    "a crowded historical castle with tourists in the style of Where's Waldo, detailed architectural scene",
    "a packed outdoor food cooking competition in the style of Where's Waldo, detailed culinary illustration",
    "a busy children's indoor play area in the style of Where's Waldo, detailed family scene",
    "a crowded outdoor hang gliding meeting point in the style of Where's Waldo, detailed adventure illustration",
    "a large space observatory with visitors in the style of Where's Waldo, detailed scientific scene",
    "a busy comic book drawing workshop with artists in the style of Where's Waldo, detailed creative illustration",
    "a crowded outdoor synchronized swimming event in the style of Where's Waldo, detailed aquatic scene",
    "a packed holiday shopping mall with shoppers in the style of Where's Waldo, detailed seasonal illustration",
    "a busy wildflower garden with botanists in the style of Where's Waldo, detailed nature scene",
    "a crowded outdoor archery tournament with competitors in the style of Where's Waldo, detailed sporting illustration",
    "a large indoor trampoline competition with athletes in the style of Where's Waldo, detailed action scene",
    "a busy outdoor puppet theater with audience in the style of Where's Waldo, detailed entertainment illustration",
    "a crowded hot spring resort with bathers in the style of Where's Waldo, detailed relaxation scene",
    "a packed bird watching tour with ornithologists in the style of Where's Waldo, detailed nature illustration",
    "a busy international food festival with vendors in the style of Where's Waldo, detailed cultural scene",
    "a crowded outdoor kite surfing competition with athletes in the style of Where's Waldo, detailed water sports illustration",
    "a large cat show with felines and owners in the style of Where's Waldo, detailed pet scene",
    "a busy international dance competition with performers in the style of Where's Waldo, detailed cultural illustration",
    "a crowded outdoor sailing regatta with sailors in the style of Where's Waldo, detailed nautical scene",
    "a packed holiday light festival with visitors in the style of Where's Waldo, detailed seasonal illustration",
    "a busy outdoor pottery kiln firing event in the style of Where's Waldo, detailed crafting scene",
    "a crowded marathon finish line with runners in the style of Where's Waldo, detailed sporting illustration",
    "a large outdoor falconry exhibition with trainers in the style of Where's Waldo, detailed nature scene",
    "a busy art restoration studio with conservators in the style of Where's Waldo, detailed cultural illustration"
]

@bot.event
async def on_ready():
    """Event fired when the bot successfully connects to Discord"""
    print(f"Bot is logged in as {bot.user}")
    print("=" * 40)
    print("WHERE'S BENNY BOT IS READY!")
    print("=" * 40)

def adjust_transparency(img, alpha_factor=0.85):
    """Adjust the transparency of an image"""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    # Get the alpha channel
    data = img.getdata()
    new_data = []

    for item in data:
        # Apply alpha factor to the alpha channel (index 3)
        new_data.append((item[0], item[1], item[2], int(item[3] * alpha_factor) if len(item) > 3 else 255))

    img.putdata(new_data)
    return img

def resize_benny(background_img, min_height_percent=0.03, max_height_percent=0.08):
    """Resize Benny image to maintain proportions and scale appropriately for the scene"""
    try:
        # Open original Benny image
        benny_img = Image.open(BENNY_IMAGE_PATH)

        # Get background dimensions
        bg_width, bg_height = background_img.size

        # Calculate appropriate size range based on the background size
        # This makes Benny proportional to the scene - smaller in landscapes with many tiny people
        # and larger in closer-up scenes
        min_height = int(bg_height * min_height_percent)  # Minimum 3% of image height
        max_height = int(bg_height * max_height_percent)  # Maximum 8% of image height

        # Choose a random size within the appropriate range
        new_height = random.randint(min_height, max_height)

        # Calculate proportional width
        width, height = benny_img.size
        new_width = int((new_height/height) * width)

        # Resize image
        resized_benny = benny_img.resize((new_width, new_height))

        # Add slight transparency to help blend with the scene
        resized_benny = adjust_transparency(resized_benny, alpha_factor=0.9)

        return resized_benny
    except Exception as e:
        print(f"Error resizing Benny: {e}")
        return None

def place_benny_on_background(background_img):
    """Place Benny on a random location in the background"""
    try:
        # Get background dimensions
        bg_width, bg_height = background_img.size

        # Check if Benny image exists
        if not os.path.exists(BENNY_IMAGE_PATH):
            print(f"ERROR: Benny image not found at {BENNY_IMAGE_PATH}")
            return background_img

        # Resize Benny to a size appropriate for the scene
        benny_img = resize_benny(background_img)  # Smart sizing based on background
        if not benny_img:
            return background_img

        b_width, b_height = benny_img.size
        print(f"Benny sized to: {b_width}x{b_height} pixels (proportional to scene)")

        # Place Benny in a more interesting position - avoid dead center
        # Divide the image into a 3x3 grid and choose one of the 9 cells
        grid_x = random.randint(0, 2)  # 0, 1, or 2
        grid_y = random.randint(0, 2)  # 0, 1, or 2

        # Calculate the bounds of the selected grid cell
        cell_width = bg_width // 3
        cell_height = bg_height // 3
        cell_x_start = grid_x * cell_width
        cell_y_start = grid_y * cell_height

        # Place Benny randomly within the selected grid cell
        x_max = min(cell_x_start + cell_width, bg_width) - b_width
        y_max = min(cell_y_start + cell_height, bg_height) - b_height
        x_pos = random.randint(cell_x_start, max(cell_x_start, x_max))
        y_pos = random.randint(cell_y_start, max(cell_y_start, y_max))

        print(f"Placing Benny at position: ({x_pos}, {y_pos}) in grid cell ({grid_x}, {grid_y})")

        # Create a composite image
        result_img = background_img.copy()

        # Paste Benny onto the background
        result_img.paste(benny_img, (x_pos, y_pos), benny_img)

        return result_img
    except Exception as e:
        print(f"Error placing Benny: {e}")
        return background_img

# Add function to check if a user has an active game
def user_has_active_game(user_id):
    """Check if a user has an active game"""
    current_time = time.time()

    # Check all active games
    for game_id, game_data in web_server.active_games.items():
        # If game hasn't expired and was created by this user
        if game_data["expiry_time"] > current_time and str(game_data["creator_user_id"]) == str(user_id):
            return game_id
    return None

@bot.command(name='whereisbenny', aliases=['wib'])
async def where_is_benny(ctx):
    """Generate a Where's Waldo style image featuring Benny with clickable web interface"""
    global headers
    global generating_image

    # Avoid multiple simultaneous image generations
    if generating_image:
        await ctx.send("I'm already generating an image! Please wait a moment.")
        return

    # Check if the user already has an active game
    active_game = user_has_active_game(ctx.author.id)
    if active_game:
        # Get the game URL
        base_url = web_server.get_public_url()
        game_url = f"{base_url}/game/{active_game}"

        # Send a sassy message
        await ctx.send(f"😒 **{ctx.author.name}** tried to generate another game without finishing the current one, what a fucking loser... 😒\n\nFinish your game first: {game_url}")
        return

    try:
        # Set the flag to indicate we're generating an image
        generating_image = True

        async with ctx.typing():
            # Send initial message
            processing_msg = await ctx.send("Generating a 'Where's Benny?' image... This might take a minute!")

            # Choose a random background prompt
            background_prompt = random.choice(BACKGROUND_PROMPTS)

            # Create prompt for Hugging Face - just generate the background
            prompt = f"{background_prompt}, without any specific characters, highly detailed cartoon illustration"

            # Generate image using Hugging Face
            payload = {
                "inputs": prompt,
                "parameters": {
                    "negative_prompt": "blurry, distorted, low quality"
                }
            }

            # Send request to Hugging Face
            response = requests.post(HUGGINGFACE_API_URL, headers=headers, json=payload)

            # Check if the model is still loading
            while response.status_code == 503 and "estimated_time" in response.json():
                wait_time = response.json()["estimated_time"]
                await processing_msg.edit(content=f"The image generation model is still loading. Waiting for {wait_time} seconds...")
                time.sleep(min(wait_time, 10))
                response = requests.post(HUGGINGFACE_API_URL, headers=headers, json=payload)

            # Get the image data
            if response.status_code == 200:
                # Convert the response to an image
                background_img = Image.open(io.BytesIO(response.content))

                # Calculate Benny's size and position
                benny_img = resize_benny(background_img)
                if not benny_img:
                    await ctx.send("Sorry, I couldn't process Benny's image.")
                    return

                b_width, b_height = benny_img.size

                # Place Benny in a random grid cell
                bg_width, bg_height = background_img.size
                grid_x = random.randint(0, 2)  # 0, 1, or 2
                grid_y = random.randint(0, 2)  # 0, 1, or 2
                cell_width = bg_width // 3
                cell_height = bg_height // 3
                cell_x_start = grid_x * cell_width
                cell_y_start = grid_y * cell_height
                x_max = min(cell_x_start + cell_width, bg_width) - b_width
                y_max = min(cell_y_start + cell_height, bg_height) - b_height
                x_pos = random.randint(cell_x_start, max(cell_x_start, x_max))
                y_pos = random.randint(cell_y_start, max(cell_y_start, y_max))

                # Create a composite image
                final_img = background_img.copy()
                final_img.paste(benny_img, (x_pos, y_pos), benny_img)

                # Delete the processing message
                await processing_msg.delete()

                # Create a web game using the web server
                creator_name = ctx.author.name
                creator_id = ctx.author.id
                discord_channel_id = ctx.channel.id

                # Register the game with the web server
                game_id, game_url = web_server.create_game(
                    final_img, x_pos, y_pos, b_width, b_height,
                    discord_channel_id, creator_id, creator_name,
                    web_server.finder_callback
                )

                # Send a message with the game link
                # Ensure the game URL is properly formatted for Discord's markdown links
                # Discord requires full URLs with protocol for clickable links
                if not game_url.startswith(("http://", "https://")):
                    game_url = f"http://{game_url}"

                # Debug info - log full URL (can be removed later)
                print(f"Generated game URL: {game_url}")

                embed = discord.Embed(
                    title="🔍 Where's Benny? 🔍",
                    description=f"**{creator_name}** has created a new 'Where's Benny?' game!",
                    color=0x3498db
                )
                embed.add_field(name="How to Play", value="Click on Benny when you find him in the image.", inline=False)
                embed.add_field(name="Time Limit", value="The game expires in 5 minutes.", inline=False)

                # Use URL as both text and link to ensure it displays properly
                embed.add_field(
                    name="Play Now",
                    value=f"[Click here to play]({game_url})\n\nIf the link doesn't work, copy this URL: {game_url}",
                    inline=False
                )
                embed.set_footer(text="First one to find Benny wins!")

                await ctx.send(embed=embed)
            else:
                await processing_msg.edit(content=f"Error generating image: {response.status_code} - {response.text}")

    except Exception as e:
        await ctx.send(f"Sorry, I couldn't generate a 'Where's Benny?' image: {str(e)}")

    finally:
        # Reset the flag when done
        generating_image = False

@bot.event
async def on_message(message):
    """Handle incoming messages"""
    # Don't respond to the bot's own messages
    if message.author == bot.user:
        return

    # Check if the message contains the trigger phrase
    if message.content.lower() == "where is benny?":
        user_id = str(message.author.id)
        current_time = time.time()

        # First check if we're already generating an image
        global generating_image
        if generating_image:
            await message.channel.send("I'm already generating an image. Please wait...")
            return

        # Check if the user already has an active game
        active_game = user_has_active_game(message.author.id)
        if active_game:
            # Get the game URL
            base_url = web_server.get_public_url()
            game_url = f"{base_url}/game/{active_game}"

            # Send a sassy message
            await message.channel.send(f"😒 **{message.author.name}** tried to generate another game without finishing the current one, what a fucking loser... 😒\n\nFinish your game first: {game_url}")
            return

        # Check if this user has generated an image recently (within cooldown period)
        if user_id in last_generated and current_time - last_generated[user_id] < 600:  # 10 minute cooldown
            # Calculate remaining cooldown
            remaining = int(600 - (current_time - last_generated[user_id]))
            minutes = remaining // 60
            seconds = remaining % 60

            # Send cooldown message
            await message.channel.send(f"{message.author.mention} You need to wait {minutes}m {seconds}s before generating another image.")
            return
        else:
            # Update timestamp for this user
            last_generated[user_id] = current_time

            # Process the request
            ctx = await bot.get_context(message)
            if ctx.valid:
                await where_is_benny(ctx)
            else:
                # Create a custom context if needed
                await message.channel.trigger_typing()
                await where_is_benny(ctx)
    else:
        # Process commands
        await bot.process_commands(message)

@bot.command(name='bennyhelp')
async def benny_help_command(ctx):
    """Display help information about the bot"""
    help_message = """
**Where's Benny Bot Commands**
`Where is Benny?` - Generate a Where's Waldo style image with Benny hidden
`!whereisbenny` - Same as above, generate a Where's Waldo style image
`!wib` - Same as above, generate a Where's Waldo style image
`!bennyhelp` - Display this help message
    """
    await ctx.send(help_message)

# Callback function for when someone finds Benny
async def benny_found_callback(finder_name, channel_id, creator_name):
    try:
        # Get the channel
        channel = bot.get_channel(int(channel_id))
        if channel:
            # Send a message to the channel
            await channel.send(f"🎉 **{finder_name}** found Benny in {creator_name}'s game! 🎉")
    except Exception as e:
        print(f"Error in benny_found_callback: {e}")

# Simple wrapper to bridge the web server callbacks to async Discord methods
def finder_callback_wrapper(finder_name, channel_id, creator_name):
    bot.loop.create_task(benny_found_callback(finder_name, channel_id, creator_name))

# Store our callback in the web server module
web_server.finder_callback = finder_callback_wrapper

def main():
    """Main entry point for the bot"""
    print("Starting Where's Benny Bot on Ubuntu server...")
    print(f"Looking for Benny image at: {BENNY_IMAGE_PATH}")

    # Check for Benny image
    if os.path.exists(BENNY_IMAGE_PATH):
        print("✅ Benny image found!")
    else:
        print("❌ Benny image NOT found! Please make sure to save the image to this location.")
        print(f"Expected path: {BENNY_IMAGE_PATH}")

    # Create temp directory if it doesn't exist
    temp_dir = os.path.join(os.path.dirname(__file__), "temp")
    os.makedirs(temp_dir, exist_ok=True)
    print(f"Temp directory ready at: {temp_dir}")

    # Check for environment variables
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("ERROR: No Discord token found in environment variables!")
        print("Make sure to set DISCORD_TOKEN in your .env file or as environment variable.")
        return

    if not os.getenv("HUGGINGFACE_API_KEY"):
        print("WARNING: No Hugging Face API key found. Image generation won't work.")

    # Set server hostname if provided
    server_hostname = os.getenv("SERVER_HOSTNAME")
    if server_hostname:
        print(f"Using server hostname: {server_hostname}")

    # Initialize the web server before starting the bot
    print("Starting web server on port 9090...")
    server = web_server.initialize()
    server_url = web_server.get_public_url()
    print(f"Web server started successfully at: {server_url}")

    # Run the bot with the token
    print("Starting Discord bot...")
    try:
        bot.run(token)
    except Exception as e:
        print(f"Error starting Discord bot: {e}")

    print("Bot has stopped.")

if __name__ == "__main__":
    main()
