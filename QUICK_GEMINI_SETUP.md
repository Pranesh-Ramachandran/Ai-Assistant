# Quick Gemini API Setup Steps

## 🔑 Step 1: Get Your Gemini API Key

1. **Open this link**: https://aistudio.google.com/apikey
2. **Sign in** with your Google account  
3. **Click "Create API Key"**
4. **Choose "Create API key in new project"**
5. **Copy the generated key** (starts with "AIza...")

## ✏️ Step 2: Add Key to JARVIS

1. **Open the file**: `d:\ai\.env` (in any text editor)
2. **Find line 10**: `GEMINI_API_KEY=`
3. **Replace with**: `GEMINI_API_KEY=AIza...your_actual_key_here`
4. **Save the file**

## 🧪 Step 3: Test Configuration  

Run this command to verify it works:
```bash
python test_gemini_setup.py
```

You should see:
```
✅ GEMINI_API_KEY found: AIza...
✅ Gemini API connection successful  
✅ AI vision analysis working
🎉 All tests passed! Gemini AI Vision is ready to use.
```

## 🎯 Step 4: Try Enhanced Commands

**Voice commands:**
- "analyze what you see" 
- "describe what's on screen"
- "what do you see in detail"

**Web interface:**
- Click 👁️ Vision button
- Choose analysis options
- Get detailed AI descriptions

## ⚠️ Important Notes

- **Keep your API key secret** - never share it
- **Free tier included** - Google provides generous free usage
- **Rate limiting built-in** - JARVIS protects your quota

## ❓ Troubleshooting

**If test fails:**
1. Check API key is correctly copied (no spaces)
2. Verify internet connection
3. Make sure key starts with "AIza"

That's it! Once configured, JARVIS will have AI-powered vision analysis.