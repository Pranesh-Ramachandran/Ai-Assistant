# Gemini API Key Setup Instructions

## Step 1: Get Your Gemini API Key

1. **Visit Google AI Studio**: https://aistudio.google.com/apikey
2. **Sign in** with your Google account
3. **Create API Key**:
   - Click "Create API Key" button
   - Choose "Create API key in new project" (recommended)
   - Copy the generated API key

## Step 2: Configure JARVIS

1. **Open the .env file** in the JARVIS directory:
   ```
   d:\ai\.env
   ```

2. **Add your API key**:
   Find the line:
   ```
   GEMINI_API_KEY=
   ```
   
   Replace it with:
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```

3. **Save the file**

## Step 3: Test the Configuration

Run the vision test to verify AI analysis works:
```bash
cd d:\ai
python test_vision_system.py
```

You should now see:
- ✅ AI Vision (Gemini) in capabilities
- Detailed image descriptions instead of "Gemini couldn't describe the image"

## Step 4: Enhanced Vision Commands

With Gemini configured, you can now use:

**Voice Commands:**
```bash
"analyze what you see"          # Detailed AI description
"describe image photo.jpg"      # AI analysis of image file
"what's on my screen analyze"   # AI description of screen content
```

**Web Interface:**
- Click 👁️ Vision button → Choose analysis options
- Get detailed scene descriptions powered by AI

## Security Notes

- ⚠️ **Never share your API key**
- ⚠️ **Never commit .env file to version control** 
- ⚠️ **Keep your API key secure**

The .env file is already in .gitignore to prevent accidental commits.

## Usage Limits

- **Free Tier**: Google AI Studio provides generous free usage
- **Rate Limits**: Built-in rate limiting in JARVIS protects your quota
- **Monitoring**: Check your usage at https://aistudio.google.com/

## Troubleshooting

**If you see "Gemini couldn't describe the image":**
1. Check your API key is correctly set in .env
2. Verify you have internet connection
3. Ensure your API key hasn't expired
4. Check the console logs for specific error messages

**Test your API key:**
```python
import os
os.getenv("GEMINI_API_KEY")  # Should return your key, not None
```