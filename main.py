from rich.progress import *
from rich.console import *
from rich.panel import *
from pyfiglet import *
from termcolor import *
from colorama import *
from pystyle import *
from httpx import *
from base64 import *
from random import *
from time import *
from PIL import *
import json
import sys
import os

init(autoreset=True)
console = Console()

"""
Duplicate - A Discord Server Cloning Tool
This script allows users to clone Discord servers either by creating a new server
or by overwriting an existing one with the structure of a source server.

Author: sevenv1
Version: 1.0
"""

def loadConfig():
    """
    Loads configuration from config.json file.
    """
    try:
        with open("config.json", "r") as configFile:
            return json.load(configFile)
    except FileNotFoundError:
        logMessage("Config file not found. Creating default config...", "error")
        defaultConfig = {
            "token": "",
            "colors": {
                "success": "red",
                "error": "red",
                "info": "red",
                "warning": "red",
                "default": "red"
            }
        }
        with open("config.json", "w") as configFile:
            json.dump(defaultConfig, configFile, indent=4)
        return defaultConfig
    except json.JSONDecodeError:
        logMessage("Invalid config file.", "error")
        sys.exit(1)

def logMessage(text, level="default"):
    """
    Prints a formatted log message with timestamp and color coding
    
    Args:
        text (str): The message to display
        level (str): Message level (success, error, info, warning, or default)
    """
    config = loadConfig()
    colors = config.get("colors", {})
    
    colorMap = {
        "success": Fore.LIGHTGREEN_EX,
        "error": Fore.RED,
        "info": Fore.CYAN,
        "warning": Fore.LIGHTYELLOW_EX,
        "default": Fore.LIGHTWHITE_EX
    }
    
    prefixMap = {
        "success": f"[{Fore.LIGHTGREEN_EX}+{Fore.LIGHTWHITE_EX}]",
        "error": f"[{Fore.RED}-{Fore.LIGHTWHITE_EX}]",
        "info": f"[{Fore.CYAN}>{Fore.LIGHTWHITE_EX}]",
        "warning": f"[{Fore.LIGHTYELLOW_EX}*{Fore.LIGHTWHITE_EX}]",
        "default": f"[{Fore.LIGHTWHITE_EX}·{Fore.LIGHTWHITE_EX}]"
    }
    
    if level in prefixMap:
        prefix = prefixMap[level]
    else:
        prefix = prefixMap["default"]
    
    timestamp = f"{Fore.LIGHTWHITE_EX}[{Fore.CYAN}{strftime('%H:%M:%S')}{Fore.LIGHTWHITE_EX}]"
    
    if "[+]" in text:
        text = text.replace("[+]", prefixMap["success"])
    if "[-]" in text:
        text = text.replace("[-]", prefixMap["error"])
    if "[*]" in text:
        text = text.replace("[*]", prefixMap["warning"])
    if "[>]" in text:
        text = text.replace("[>]", prefixMap["info"])
    
    print(f"{timestamp} {prefix} {text}")

class ServerScraper:
    """
    Scrapes data from a Discord server using the Discord API.
    
    Attributes:
        token (str): Discord user token
        serverId (str): ID of the server to scrape
        baseUrl (str): Base URL for API requests
        session (Client): HTTPX client for making requests
        headers (dict): HTTP headers including authorization
    """
    
    def __init__(self, token, serverId):
        """
        Initialize the ServerScraper with token and server ID
        
        Args:
            token (str): Discord user token
            serverId (str): ID of the server to scrape
        """
        self.token = token
        self.serverId = serverId
        self.baseUrl = f"https://discord.com/api/v9/guilds/{self.serverId}"
        self.session = Client()
        self.headers = {"Authorization": self.token}
        self.config = loadConfig()
        self.settings = self.config.get("settings", {})

    def makeRequest(self, url):
        """
        Make an HTTP GET request to the Discord API
        
        Args:
            url (str): The URL to request
        
        Returns:
            dict: JSON response from the API
            
        Raises:
            Exception: If the request fails after max retries
        """
        maxRetries = self.settings.get("max_retries", 3)
        retryDelay = self.settings.get("retry_delay", 1.5)
        autoRetry = self.settings.get("auto_retry_failed_requests", True)
        
        for attempt in range(maxRetries):
            response = self.session.get(
                url=url,
                headers=self.headers,
            )
            
            if response.status_code == 200:
                return response.json()
            
            logMessage(f"Request failed: {response.status_code} - {response.text}", "error")
            
            if not autoRetry or attempt >= maxRetries - 1:
                break
                
            logMessage(f"Retrying in {retryDelay}s ({attempt+1}/{maxRetries})...", "warning")
            sleep(retryDelay)
            
        raise Exception(f"Request failed after {maxRetries} attempts")

    def getChannels(self):
        """
        Get all channels from the server
        
        Returns:
            dict: Server channels data
        """
        return self.makeRequest(f"{self.baseUrl}/channels")

    def getServerInfo(self):
        """
        Get general server information
        
        Returns:
            dict: Server information
        """
        return self.makeRequest(self.baseUrl)

    def collectServerData(self):
        """
        Collect all necessary data from the server
        
        Returns:
            dict: Complete server data including info, channels, roles, emojis
        """
        serverInfo = self.getServerInfo()
        serverChannels = self.getChannels()

        return {
            "info": serverInfo,
            "channels": serverChannels,
            "roles": serverInfo.get("roles", []),
            "emojis": serverInfo.get("emojis", []),
            "features": serverInfo.get("features", []),
            "system_channel_id": serverInfo.get("system_channel_id"),
            "verification_level": serverInfo.get("verification_level", 0),
            "default_message_notifications": serverInfo.get("default_message_notifications", 0),
            "explicit_content_filter": serverInfo.get("explicit_content_filter", 0),
        }

class ServerCreator:
    def __init__(self, token, serverData):
        self.token = token
        self.baseUrl = "https://discord.com/api/v9"
        self.session = Client()
        self.serverData = serverData
        self.headers = {"Authorization": self.token}
        self.config = loadConfig()
        self.requestDelay = 0.75
        self.serverId = None
        self.everyoneRoleId = None
        self.roleMap = {}
        self.channelMap = {}

    def createServer(self):
        """
        Creates a new Discord server based on source server data
        
        Returns:
            bool: True if server creation was successful, False otherwise
        """
        logMessage("Creating new server", "info")
        
        try:
            serverIcon = None
            
            if self.serverData['info'].get('icon'):
                imgUrl = f"https://cdn.discordapp.com/icons/{self.serverData['info']['id']}/{self.serverData['info']['icon']}.webp?size=96"
                try:
                    imgResponse = self.session.get(imgUrl)
                    if imgResponse.status_code == 200:
                        serverIcon = f"data:image/png;base64,{b64encode(imgResponse.content).decode('utf-8')}"
                    else:
                        logMessage(f"Failed to download server icon: {imgResponse.status_code}", "error")
                except Exception as e:
                    logMessage(f"Error downloading server icon: {e}", "error")
                
            serverData = {
                "name": self.serverData["info"]["name"],
                "icon": serverIcon,
                "channels": [],
                "system_channel_id": None,
                "guild_template_code": "8ewECn5UKpDY",
            }

            response = self.session.post(
                url=f"{self.baseUrl}/guilds",
                headers=self.headers,
                json=serverData,
            )
            
            if response.status_code != 201:
                logMessage(f"Failed to create server: {response.status_code} - {response.text}", "error")
                return False

            responseData = response.json()
            
            self.serverId = responseData["id"]
            self.everyoneRoleId = responseData["roles"][0]["id"]
            
            logMessage(f"Created server: {self.serverData['info']['name']} (ID: {self.serverId})", "success")
            
            self._updateEveryoneRole()
            self._updateServerSettings()
            
            return True
        except Exception as e:
            logMessage(f"Error creating server: {e}", "error")
            return False

    def _updateEveryoneRole(self):
        """
        Updates the @everyone role permissions in the new server
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            url = f"{self.baseUrl}/guilds/{self.serverId}/roles/{self.everyoneRoleId}"
            
            everyoneRoleData = next((role for role in self.serverData["roles"] if role["name"] == "@everyone"), None)
            if everyoneRoleData:
                permissions = everyoneRoleData.get("permissions", "1071698529857")
            else:
                permissions = "1071698529857"
                
            roleData = {
                "name": "@everyone",
                "permissions": permissions,
                "color": 0,
                "hoist": False,
                "mentionable": False,
                "icon": None,
                "unicode_emoji": None,
            }
            
            response = self.session.patch(
                url=url,
                headers=self.headers,
                json=roleData,
            )
            
            if response.status_code != 200:
                logMessage(f"Failed to update @everyone role: {response.status_code}", "error")
                return False
                
            logMessage("Updated @everyone role permissions", "success")
            return True
        except Exception as e:
            logMessage(f"Error updating @everyone role: {e}", "error")
            return False

    def _updateServerSettings(self):
        """
        Updates server settings based on source server configuration
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            url = f"{self.baseUrl}/guilds/{self.serverId}"
            
            serverSettings = {
                "features": self.serverData.get("features", ["APPLICATION_COMMAND_PERMISSIONS_V2", "COMMUNITY"]),
                "verification_level": self.serverData.get("verification_level", 1),
                "default_message_notifications": self.serverData.get("default_message_notifications", 1),
                "explicit_content_filter": self.serverData.get("explicit_content_filter", 2),
                "rules_channel_id": "1", 
                "public_updates_channel_id": "1",
            }
            
            response = self.session.patch(
                url=url,
                headers=self.headers,
                json=serverSettings,
            )
            
            if response.status_code != 200:
                logMessage(f"Failed to update server settings: {response.status_code}", "error")
                return False
                
            logMessage("Updated server settings", "success")
            return True
        except Exception as e:
            logMessage(f"Error updating server settings: {e}", "error")
            return False

    def deleteChannels(self):
        if not self.serverId:
            logMessage("Server ID not set", "error")
            return False
            
        try:
            response = self.session.get(
                url=f"{self.baseUrl}/guilds/{self.serverId}/channels",
                headers=self.headers,
            )
            
            if response.status_code != 200:
                logMessage(f"Failed to get channels: {response.status_code}", "error")
                return False
                
            existingChannels = response.json()
            
            for channel in existingChannels:
                deleteResponse = self.session.delete(
                    url=f"{self.baseUrl}/channels/{channel['id']}",
                    headers=self.headers,
                )
                
                if deleteResponse.status_code == 200:
                    logMessage(f"Deleted channel: {channel['name']}", "success")
                else:
                    logMessage(f"Failed to delete channel: {channel['name']}", "error")
                    
                sleep(self.requestDelay)
            
            return True
        except Exception as e:
            logMessage(f"Error deleting channels: {e}", "error")
            return False

    def createRoles(self):
        """
        Creates roles in the target server based on source server roles
        
        Returns:
            dict: Mapping between source role IDs and target role IDs
        """
        if not self.serverId:
            logMessage("Server ID not set, can't create roles", "error")
            return {}
            
        try:
            serverRoles = self.serverData["roles"]
            serverRoles = sorted(serverRoles, key=lambda x: x["position"], reverse=True)
            
            logMessage(f"Creating {len(serverRoles)} roles", "info")
            
            for role in serverRoles:
                if role["name"] == "@everyone":
                    self.roleMap[role["id"]] = self.everyoneRoleId
                    
                    for channel in self.serverData["channels"]:
                        for permission in channel.get("permission_overwrites", []):
                            if permission["id"] == role["id"]:
                                permission["id"] = self.everyoneRoleId
                    continue

                roleData = {
                    "name": role["name"],
                    "permissions": role["permissions"],
                    "color": role["color"],
                    "hoist": role["hoist"],
                    "mentionable": role["mentionable"],
                    "icon": None,
                    "unicode_emoji": None,
                }

                response = self.session.post(
                    url=f"{self.baseUrl}/guilds/{self.serverId}/roles",
                    headers=self.headers,
                    json=roleData,
                )

                if response.status_code == 200:
                    newRoleId = response.json()["id"]
                    self.roleMap[role["id"]] = newRoleId
                    
                    for channel in self.serverData["channels"]:
                        for permission in channel.get("permission_overwrites", []):
                            if permission["id"] == role["id"]:
                                permission["id"] = newRoleId
                else:
                    logMessage(f"Failed to create role: {role['name']}", "error")

                sleep(self.requestDelay)
                
            return self.roleMap
        except Exception as e:
            logMessage(f"Error creating roles: {e}", "error")
            return {}

    def createChannels(self):
        """
        Creates channels in the target server based on source server channels
        
        Returns:
            dict: Mapping between source channel IDs and target channel IDs
        """
        if not self.serverId:
            logMessage("Server ID not set, can't create channels", "error")
            return {}
            
        try:
            parentChannels = sorted(
                [channel for channel in self.serverData["channels"] if channel["type"] == 4],
                key=lambda x: x["position"]
            )
            otherChannels = [channel for channel in self.serverData["channels"] if channel["type"] != 4]
            
            logMessage(f"Creating {len(parentChannels)} categories", "info")
            
            for category in parentChannels:
                categoryData = {
                    "name": category["name"],
                    "type": category["type"],
                    "permission_overwrites": category.get("permission_overwrites", []),
                }

                response = self.session.post(
                    url=f"{self.baseUrl}/guilds/{self.serverId}/channels",
                    headers=self.headers,
                    json=categoryData,
                )

                if response.status_code == 201:
                    newCategoryId = response.json()["id"]
                    self.channelMap[category["id"]] = newCategoryId
                    logMessage(f"Created category: {category['name']}", "success")
                else:
                    logMessage(f"Failed to create category: {category['name']}", "error")

                sleep(self.requestDelay)
                
            logMessage(f"Creating {len(otherChannels)} channels", "info")
            
            for channel in otherChannels:
                channelData = {
                    "name": channel["name"],
                    "type": channel["type"],
                    "permission_overwrites": channel.get("permission_overwrites", []),
                }

                if channel.get("parent_id") and channel["parent_id"] in self.channelMap:
                    channelData["parent_id"] = self.channelMap[channel["parent_id"]]

                if channel["type"] == 0:
                    if channel.get("topic"):
                        channelData["topic"] = channel["topic"]
                    if channel.get("rate_limit_per_user"):
                        channelData["rate_limit_per_user"] = channel["rate_limit_per_user"]
                    if channel.get("nsfw"):
                        channelData["nsfw"] = channel["nsfw"]
                elif channel["type"] == 2:
                    if channel.get("bitrate"):
                        channelData["bitrate"] = channel["bitrate"]
                    if channel.get("user_limit"):
                        channelData["user_limit"] = channel["user_limit"]

                response = self.session.post(
                    url=f"{self.baseUrl}/guilds/{self.serverId}/channels",
                    headers=self.headers,
                    json=channelData,
                )

                if response.status_code == 201:
                    newChannelId = response.json()["id"]
                    self.channelMap[channel["id"]] = newChannelId
                    logMessage(f"Created channel: {channel['name']}", "success")
                else:
                    logMessage(f"Failed to create channel: {channel['name']}", "error")

                sleep(self.requestDelay)
            
            return self.channelMap
        except Exception as e:
            logMessage(f"Error creating channels: {e}", "error")
            return {}

    def createEmojis(self):
        """
        Creates emojis in the target server based on source server emojis
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.serverId:
            logMessage("Server ID not set, can't create emojis", "error")
            return False
            
        try:
            serverEmojis = self.serverData.get("emojis", [])
            
            if not serverEmojis:
                logMessage("No emojis to create", "warning")
                return True
            
            logMessage(f"Creating {len(serverEmojis)} emojis", "info")
            
            for emoji in serverEmojis:
                try:
                    imgUrl = f"https://cdn.discordapp.com/emojis/{emoji['id']}.png"
                    imgResponse = self.session.get(imgUrl)
                    
                    if imgResponse.status_code != 200:
                        logMessage(f"Failed to download emoji image: {imgResponse.status_code}", "error")
                        continue
                        
                    imgBase64 = f"data:image/png;base64,{b64encode(imgResponse.content).decode('utf-8')}"
                    
                    emojiData = {
                        "name": emoji["name"],
                        "image": imgBase64,
                        "roles": emoji.get("roles", [])
                    }
                    
                    response = self.session.post(
                        url=f"{self.baseUrl}/guilds/{self.serverId}/emojis",
                        headers=self.headers,
                        json=emojiData,
                    )
                    
                    if response.status_code == 201:
                        logMessage(f"Created emoji: {emoji['name']}", "success")
                    else:
                        logMessage(f"Failed to create emoji: {emoji['name']}", "error")
                        
                except Exception as e:
                    logMessage(f"Error creating emoji {emoji.get('name', 'unknown')}: {e}", "error")
                    
                sleep(self.requestDelay)
            
            return True
        except Exception as e:
            logMessage(f"Error creating emojis: {e}", "error")
            return False

    def executeAll(self):
        """
        Executes the complete server cloning process
        
        Returns:
            bool: True if all operations completed successfully
        """
        tasks = [
            {"name": "Server Creation", "func": self.createServer},
            {"name": "Delete Default Channels", "func": self.deleteChannels},
            {"name": "Create Roles", "func": self.createRoles},
            {"name": "Create Channels", "func": self.createChannels},
            {"name": "Create Emojis", "func": self.createEmojis},
        ]
        
        for task in tasks:
            try:
                if task["name"] == "Server Creation":
                    if not task["func"]():
                        logMessage("Server creation failed, stopping process", "error")
                        return False
                else:
                    task["func"]()
            except Exception as e:
                logMessage(f"Error in {task['name']}: {e}", "warning")
                
        return True

def displayBanner(banner):
    """
    Displays a static ASCII banner
    
    Args:
        banner (str): The banner text to display
    """
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")
    print(Fore.RED + banner)
    
def generateBanner():
    asciiText = """
  ______   ___        ______    _____  ___    _______   _______   
 /" _  "\ |"  |      /    " \  ( "   \|"  \  /"     "| /"      \  
(: ( \___)||  |     // ____  \ |.\    \    |(: ______)|:        | 
 \/ \     |:  |    /  /    ) :)|: \.   \   | \/    |  |_____/   ) 
 //  \ _   \  |___(: (____/ // |.  \    \. | // ___)_  //      /  
(:   _) \ ( \_|:   |\        /  |    \    \ |(:      "||:  __   \  
 \_______) \_______) "_____/    \___|\____\) \_______)|__|  \___)
    """
    return asciiText

def main():
    """
    Main function that runs the Discord server cloning application
    """
    try:
        config = loadConfig()
        token = config.get("token", "")
        
        if not token:
            logMessage("Token not found in config.json", "error")
            token = input(f"{Fore.RED}[?]{Fore.RESET} Enter your Discord token: ")
            
            config["token"] = token
            with open("config.json", "w") as configFile:
                json.dump(config, configFile, indent=4)

        banner = generateBanner()
        displayBanner(banner)
        
        console.print("\n[red]Select cloning mode:")
        console.print("[1] Clone to existing server")
        console.print("[2] Create new server")
        
        cloningMode = ""
        while cloningMode not in ["1", "2"]:
            cloningMode = input(f"{Fore.RED}[?]{Style.RESET_ALL} Your choice (1/2): ")
            
            if cloningMode not in ["1", "2"]:
                console.print("[red]Invalid option. Please enter 1 or 2.")
        
        sourceServerId = input(f"{Fore.RED}[?]{Style.RESET_ALL} Source Server ID: ")
        
        try:
            console.print(Panel("[bold cyan]Connecting to source server..."))
            sourceScraper = ServerScraper(token, sourceServerId)
            sourceData = sourceScraper.collectServerData()
            
            if not sourceData["info"].get("id"):
                console.print(Panel("[bold red]Failed to get source server data. Check your token and server ID."))
                input("Press any key to exit...")
                return
                
            console.print(Panel(f"[bold green]Successfully connected to source server: {sourceData['info'].get('name', 'Unknown')}"))
        except Exception as e:
            console.print(Panel(f"[bold red]Failed to connect to source server: {e}"))
            input("Press any key to exit...")
            return
        
        if cloningMode == "1":
            targetServerId = input(f"{Fore.RED}[?]{Style.RESET_ALL} Target Server ID: ")
            
            try:
                console.print(Panel("[bold cyan]Connecting to target server..."))
                targetScraper = ServerScraper(token, targetServerId)
                targetData = targetScraper.collectServerData()
                
                if not targetData["info"].get("id"):
                    console.print(Panel("[bold red]Failed to get target server data. Check your token and server ID."))
                    input("Press any key to exit...")
                    return
                    
                console.print(Panel(f"[bold green]Successfully connected to target server: {targetData['info'].get('name', 'Unknown')}"))
                
                console.print(Panel("[bold yellow]WARNING: This will delete all existing channels and roles in the target server!"), style="yellow")
                confirmation = input(f"{Fore.RED}[!]{Style.RESET_ALL} Are you sure you want to continue? (yes/no): ")
                
                if confirmation.lower() != "yes":
                    console.print(Panel("[bold yellow]Operation cancelled by user."))
                    input("Press any key to exit...")
                    return
                    
                serverCreator = ServerCreator(token, sourceData)
                serverCreator.serverId = targetServerId
                
                for role in targetData["roles"]:
                    if role["name"] == "@everyone":
                        serverCreator.everyoneRoleId = role["id"]
                        break
                
                serverCreator.deleteChannels()
                serverCreator.createRoles()
                serverCreator.createChannels()
                serverCreator.createEmojis()
                
            except Exception as e:
                console.print(Panel(f"[bold red]Error cloning to existing server: {e}"))
        else:
            try:
                serverCreator = ServerCreator(token, sourceData)
                serverCreator.executeAll()
            except Exception as e:
                console.print(Panel(f"[bold red]Error creating new server: {e}"))
        
        console.print(Panel("[bold green]Server cloning process completed!"))
        input("Press any key to exit...")
    except KeyboardInterrupt:
        console.print(Panel("[bold yellow]Operation cancelled by user."))
    except Exception as e:
        console.print(Panel(f"[bold red]Unexpected error: {e}"))
        input("Press any key to exit...")

if __name__ == "__main__":
    System.Title("Duplicate - Discord Server Cloning Tool - made by github.com/sevenv1")
    main()