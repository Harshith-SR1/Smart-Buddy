# ⚡ Smart Buddy - Quick Start Guide

Get Smart Buddy running in **under 5 minutes**!

---

## 🚀 Option 1: One-Line Setup (Recommended)

### Windows (PowerShell)
```powershell
.\scripts\run_localhost.ps1
```

### Linux/Mac (Bash)
```bash
./scripts/run_localhost.sh
```

**That's it!** Open http://localhost:8000/chat-ui and start chatting.

---

## 📦 Option 2: Manual Setup

### Prerequisites
- Python 3.11 or higher
- pip (Python package manager)
- Google API key ([Get one here](https://aistudio.google.com/app/apikey))

### Step-by-Step

**1. Clone the repository**
```bash
git clone https://github.com/yourusername/smart-buddy
cd smart-buddy
```

**2. Create virtual environment**
```powershell
# Windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Set up your Google API key**
```powershell
# Windows (PowerShell)
$env:GOOGLE_API_KEY="your-api-key-here"

# Linux/Mac (Bash)
export GOOGLE_API_KEY="your-api-key-here"
```

**5. Run the server**
```bash
python server_flask.py
```

**6. Open your browser**
```
http://localhost:8000/chat-ui
```

---

## 🐳 Option 3: Docker (No Python Install Needed)

**1. Build and run**
```bash
docker-compose up
```

**2. Access the app**
```
http://localhost:8000/chat-ui
```

**Stop the container:**
```bash
docker-compose down
```

---

## 🎯 First Steps in Smart Buddy

### 1. Choose Your Mode
Click the dropdown at the top to select:
- **🤖 General** - Tasks, calendar, general chat
- **🎓 Mentor** - Learning and teaching
- **💕 BestFriend** - Emotional support

### 2. Try These Examples

**General Mode:**
```
Add task to finish project by Friday
Schedule meeting tomorrow at 2pm
What's quantum computing?
```

**Mentor Mode:**
```
Teach me about neural networks
Help me plan a 30-day Python roadmap
Explain recursion with examples
```

**BestFriend Mode:**
```
I'm stressed about exams
I got promoted today!
Need some motivation
```

### 3. Try Multi-Modal Features

**Voice Input:**
- Click the 🎤 microphone button
- Speak your message
- Watch it transcribe automatically

**Image Upload:**
- Click the 📎 attachment button
- Select an image (PNG, JPG, GIF)
- Smart Buddy will analyze it with Gemini Vision

**Video Upload:**
- Click the 📎 attachment button
- Select a video file (up to 50MB)
- Smart Buddy will process the video content

---

## 🔍 Verify Installation

### Check all features are working:

**1. Test API Connection**
```bash
python -c "import google.generativeai as genai; print('Gemini API: OK')"
```

**2. Test Memory System**
```bash
python -c "from smart_buddy.memory import MemoryBank; print('Memory: OK')"
```

**3. Test MCP Servers**
```bash
python -c "from smart_buddy.tools.base import get_available_tools; print(f'Tools: {len(get_available_tools())}')"
```

**Expected output:**
```
Gemini API: OK
Memory: OK
Tools: 9
```

---

## 📊 View Metrics Dashboard

While the server is running, visit:
```
http://localhost:8000/metrics
```

You'll see:
- Response time statistics
- Token usage tracking
- Agent routing statistics
- Error rates (should be near 0%)

---

## 🐛 Troubleshooting

### "Module not found" error
```bash
pip install -r requirements.txt
```

### "API key not set" error
Set your Google API key in environment:
```powershell
# Windows
$env:GOOGLE_API_KEY="your-key-here"

# Linux/Mac
export GOOGLE_API_KEY="your-key-here"
```

### Port 8000 already in use
Change the port in `server_flask.py`:
```python
app.run(host='0.0.0.0', port=8080, debug=True)
```

### Voice input not working
- **Chrome/Edge:** Supported natively
- **Firefox:** May need permissions
- **Safari:** Limited support
- Try using text input if voice fails

### Slow responses
- Check your internet connection
- Gemini API calls require network access
- First request may be slower (model loading)
- Subsequent requests: ~1-2 seconds

---

## 📱 Mobile Access

Smart Buddy works on mobile browsers!

**From your phone:**
1. Find your computer's local IP (e.g., 192.168.1.100)
2. Open: `http://192.168.1.100:8000/chat-ui`
3. Works best in Chrome/Safari mobile

**Note:** Voice input may have limited mobile support.

---

## 🎓 Learn More

### Documentation
- **Full Guide:** `README.md`
- **Architecture:** See Mermaid diagram in `README.md`
- **Development Journey:** `DEVELOPMENT_JOURNEY.md`
- **MCP Integration:** `docs/mcp_integration.md`
- **Multimedia Features:** `docs/multimedia_features.md`

### Code Examples
- **Kaggle Notebook:** `Smart_Buddy_Showcase.ipynb`
- **Demo Video Script:** `DEMO_VIDEO_SCRIPT.md`
- **Submission Guide:** `SUBMISSION_GUIDE.md`

### Testing
```bash
# Run evaluation suite
python scripts/run_eval.py

# Run benchmarks
python scripts/run_ci_benchmarks.py
```

---

## 🎯 Quick Feature Checklist

After starting Smart Buddy, verify these features work:

- [ ] Chat interface loads at http://localhost:8000/chat-ui
- [ ] Can select different modes (General, Mentor, BestFriend)
- [ ] Can send text messages and get responses
- [ ] Voice input button appears (microphone icon)
- [ ] File upload button works (attachment icon)
- [ ] Metrics dashboard accessible at /metrics
- [ ] Responses appear within 1-3 seconds
- [ ] Memory persists across messages (try "remember my name is X")
- [ ] Different modes show different personalities

---

## 💡 Pro Tips

### For Best Performance
1. **Use Chrome or Edge** for full voice support
2. **Keep conversation focused** for better context
3. **Switch modes** based on your needs
4. **Upload images** for visual analysis
5. **Check /metrics** to see system performance

### For Development
1. Server auto-reloads on file changes (Flask debug mode)
2. Logs saved to console in JSON format
3. Memory stored in `smart_buddy.db` (SQLite)
4. Trace IDs help debug agent routing

### For Demos
1. Prepare example questions for each mode
2. Show voice input with microphone button
3. Upload a sample image to demonstrate Vision API
4. Display /metrics dashboard for observability
5. Switch between modes to show personality changes

---

## 🚀 Next Steps

1. **Try all three modes** to see personality differences
2. **Upload an image** to test Gemini Vision
3. **Use voice input** for hands-free interaction
4. **Check the metrics** dashboard to see performance
5. **Read the docs** for advanced features

---

## 📞 Need Help?

- **Issues?** Check `README.md` troubleshooting section
- **Questions?** Read `SUBMISSION_GUIDE.md`
- **Code details?** Explore `docs/` folder
- **Examples?** Run `Smart_Buddy_Showcase.ipynb`

---

**Enjoy using Smart Buddy!** 🎉

*Your adaptive AI companion is ready to help with tasks, learning, and emotional support.*

---

**Estimated Setup Time:** 2-5 minutes  
**Minimum Requirements:** Python 3.11+, Google API key, 500MB disk space  
**Tested On:** Windows 11, Ubuntu 22.04, macOS Ventura
