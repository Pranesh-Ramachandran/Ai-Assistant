# 🤖 Jarvis AI Assistant

A sophisticated AI assistant inspired by Iron Man's JARVIS, built with Python and Kivy for cross-platform deployment including Android.

## ✨ Features

### 🎯 Core Features
- **Voice Wake Word Detection**: Say "Hey Jarvis" to activate
- **Multi-modal Input**: Voice and text input support
- **Real-time Animations**: Animated UI with pulsing rings and smooth transitions
- **Cross-platform**: Works on Windows, Linux, macOS, and Android

### 🔐 Authentication System
- **Voice Authentication**: Register and login with voice samples
- **Text Fallback**: Backup login with username/password
- **Secure Storage**: Encrypted password storage with voice profiles

### 🎫 Ticket Booking System
- **Real Seat Selection**: Interactive 5x10 seat layout
- **Multiple Theaters**: Choose from various cinema locations
- **Live Movie Data**: Current movies with ratings and showtimes
- **Payment Integration**: Simulated payment processing
- **Booking History**: Track all your bookings

### 🌐 Connectivity Features
- **WiFi Status Monitoring**: Real-time connection status
- **Online/Offline Mode**: Graceful degradation when offline
- **Location Services**: GPS and IP-based location detection

### 🎮 Additional Modules
- **IoT Control**: Smart home device integration
- **Games Module**: Built-in entertainment
- **Weather Information**: Current weather and forecasts
- **Web Search**: Integrated search capabilities

### 📱 Mobile-Ready
- **Android Permissions**: Microphone, location, storage access
- **Touch-Friendly UI**: Optimized for mobile interaction
- **Hamburger Menu**: Easy navigation between features
- **Responsive Design**: Adapts to different screen sizes

## 🚀 Quick Start

### Prerequisites
```bash
# Install Python 3.8+
# Install required packages
pip install -r requirements.txt
```

### Desktop Usage
```bash
# Run the application
python main.py
```

### Android Deployment
```bash
# Install buildozer
pip install buildozer

# Run deployment script
./deploy.sh  # Linux/macOS
deploy.bat   # Windows

# Or manually build
buildozer android debug
```

## 📋 Installation Guide

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd AI_Assistant
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. First Run Setup
1. Run `python main.py`
2. Register a new user with voice samples
3. Grant microphone permissions
4. Start using Jarvis!

### 4. Android Build
```bash
# Generate app assets
python create_assets.py

# Build APK
buildozer android debug

# Install on device
adb install bin/jarvis_ai-1.0-debug.apk
```

## 🎯 Usage Guide

### Voice Commands
- **"Hey Jarvis"** - Wake up the assistant
- **"Book tickets"** - Open ticket booking
- **"What time is it?"** - Get current time
- **"Turn on lights"** - IoT control (if configured)
- **"Play a game"** - Launch games module
- **"What's the weather?"** - Weather information

### UI Navigation
- **Hamburger Menu** (☰) - Access all features
- **Voice Button** (🎤) - Manual voice activation
- **Text Input** - Type commands directly
- **Settings** - Configure preferences

### Ticket Booking Flow
1. Say "Book tickets" or use hamburger menu
2. Select movie from available options
3. Choose theater and showtime
4. Pick seats from interactive layout
5. Confirm booking and payment
6. Receive booking confirmation

## 🔧 Configuration

### Voice Settings
- Adjust wake word sensitivity in `voice_auth.py`
- Add custom wake words
- Configure voice recognition timeout

### API Integration
- Add TMDB API key for live movie data
- Configure location services
- Set up payment gateway (for production)

### IoT Integration
- Configure smart home devices
- Set up device control protocols
- Add custom IoT commands

## 📱 Android Permissions

The app requests these permissions:
- **RECORD_AUDIO**: Voice commands and authentication
- **ACCESS_FINE_LOCATION**: Location-based services
- **INTERNET**: Online features and API calls
- **WRITE_EXTERNAL_STORAGE**: Save user data and bookings

## 🛠️ Development

### Project Structure
```
AI_Assistant/
├── main.py                 # Main application entry
├── voice_auth.py          # Voice authentication system
├── enhanced_booking.py    # Ticket booking system
├── jarvis_brain.py        # AI decision making
├── iot_assistant.py       # IoT control module
├── game_module.py         # Games and entertainment
├── data_collector.py      # Information gathering
├── requirements.txt       # Python dependencies
├── buildozer.spec        # Android build configuration
└── deploy.sh/bat         # Deployment scripts
```

### Adding New Features
1. Create new module in project directory
2. Import in `main.py`
3. Add UI components to appropriate screens
4. Update intent recognition in `jarvis_brain.py`
5. Test on desktop before Android build

### Customization
- **Themes**: Modify colors in UI components
- **Animations**: Adjust timing in `JarvisRing` class
- **Voice**: Change TTS voice properties
- **Layout**: Modify screen layouts and components

## 🐛 Troubleshooting

### Common Issues

**Voice not working on Android:**
- Ensure microphone permission is granted
- Check if device has Google Speech Services
- Try text input as fallback

**Build fails:**
- Update buildozer: `pip install --upgrade buildozer`
- Clear build cache: `buildozer android clean`
- Check Android SDK/NDK versions

**App crashes on startup:**
- Check device Android version (minimum API 21)
- Verify all permissions are granted
- Check logs: `adb logcat | grep python`

### Performance Tips
- Close unused background apps
- Ensure stable internet connection
- Grant all requested permissions
- Use voice commands in quiet environment

## 🔮 Future Enhancements

### Planned Features
- **AI Chat Integration**: GPT/Claude integration
- **Smart Home Hub**: Expanded IoT control
- **Calendar Integration**: Schedule management
- **News Briefing**: Daily news summaries
- **Music Control**: Spotify/YouTube integration
- **Video Calling**: Built-in communication
- **AR Features**: Camera-based interactions

### Technical Improvements
- **Offline Voice Processing**: Local STT/TTS
- **Better Animation**: 3D graphics and effects
- **Cloud Sync**: Multi-device synchronization
- **Plugin System**: Third-party extensions
- **Machine Learning**: Personalized responses

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 Support

- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Join GitHub Discussions
- **Email**: [your-email@example.com]

## 🙏 Acknowledgments

- Kivy framework for cross-platform UI
- Google Speech Recognition API
- OpenStreetMap for location services
- The open-source community

---

**Made with ❤️ by [Your Name]**

*"Sometimes you gotta run before you can walk." - Tony Stark*