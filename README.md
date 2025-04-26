# 🚀 Duplicate
A powerful Discord server cloning tool written in Python that allows you to clone servers or overwrite existing ones.

## 📖 About
This tool lets you clone Discord servers efficiently, either by creating a new server or overwriting an existing one. Built with security and ease of use in mind.

## ✨ Features
- 🔄 Clone entire server structure
- 📚 Copy all channels and categories
- 👥 Clone roles with permissions
- 😀 Transfer server emojis
- 🎯 Multiple cloning modes
- ⚡ Fast and efficient

## 🛠️ Installation

1. **Clone or download the repository**

2. **Install required packages**
```bash
pip install -r requirements.txt
```

3. **Configure your account token**
Edit `config.json` and add your Discord token:
```json
{
   "token": "your-account-token-here",
   "colors": {
      "success": "green",
      "error": "red",
      "info": "cyan",
      "warning": "yellow",
      "default": "red"
   }
}
```

## 📝 Usage

1. Run the script:
```bash
python main.py
```

2. Choose your cloning mode:
- Clone to existing server
- Create new server

3. Follow the prompts to enter server IDs and confirm actions

## ⚠️ Important Notes
- Requires Discord user token
- Admin permissions needed in target server
- Use responsibly and respect Discord's TOS
- Backup important servers before overwriting

## 🔧 Technical Details
- Written in Python
- Uses Discord API v9 (Not bot api, this is a selfbot.)
- Asynchronous HTTP requests
- Efficient error handling
- Progress tracking
- Colored console output

## 🤝 Credits
Made by: sevenv1

## ⚖️ Disclaimer
This tool is for educational purposes only. Use at your own risk and responsibility.
