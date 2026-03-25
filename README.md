# LinkedIn Automation Suite

A comprehensive Python-based LinkedIn automation toolkit that provides safe, efficient, and intelligent automation for various LinkedIn activities.

## 🚀 Features

### Core Automation

- **Secure Login**: Automated login with credential management
- **People Search**: Search and extract profile information
- **Connection Management**: Send connection requests with custom messages
- **Content Posting**: Automated content and image posting
- **Messaging**: Send messages to connections
- **Engagement**: Like posts and add comments
- **Request Management**: Accept pending connection requests

### Advanced Features

- **Anti-Detection**: Uses undetected-chromedriver to avoid bot detection
- **Human-like Behavior**: Random delays and typing patterns
- **Rate Limiting**: Built-in safety measures to respect LinkedIn limits
- **Scheduling**: Automated task scheduling with cron-like functionality
- **Logging**: Comprehensive logging for monitoring and debugging
- **Error Handling**: Robust error handling and recovery

## 📋 Prerequisites

- Python 3.7+
- Chrome browser installed
- LinkedIn account
- Valid LinkedIn credentials

## 🛠️ Installation

1. **Clone or download the project**

   ```bash
   git clone <repository-url>
   cd linkedin-automation
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   - Copy `env_example.txt` to `.env`
   - Add your LinkedIn credentials:
   ```
   LINKEDIN_EMAIL=your_email@example.com
   LINKEDIN_PASSWORD=your_password
   ```

## 🚀 Quick Start

### Basic Usage

```python
from linkedin_advanced import AdvancedLinkedInAutomation

# Initialize automation
with AdvancedLinkedInAutomation(headless=False) as linkedin:
    # Login
    if linkedin.login():
        print("Successfully logged in!")

        # Search for people
        profiles = linkedin.search_people("software engineer", "San Francisco", max_results=5)
        for profile in profiles:
            print(f"Name: {profile['name']}, Title: {profile['title']}")

        # Like some posts
        linkedin.like_posts(max_likes=3)

        # Post content
        linkedin.post_content("Hello LinkedIn! This is an automated post.")
```

### Advanced Usage with Scheduling

```python
from linkedin_scheduler import LinkedInScheduler, LinkedInTasks
from linkedin_advanced import AdvancedLinkedInAutomation

# Create scheduler
scheduler = LinkedInScheduler()
linkedin = AdvancedLinkedInAutomation(headless=False)

# Add daily tasks
scheduler.add_daily_task(
    LinkedInTasks.daily_connection_requests,
    "09:00",
    linkedin,
    max_requests=5
)

scheduler.add_daily_task(
    LinkedInTasks.daily_engagement,
    "14:00",
    linkedin,
    max_likes=10,
    max_comments=3
)

# Start scheduler
scheduler.start()
```

## 📁 Project Structure

```
linkedin-automation/
├── linkedin.py                 # Basic LinkedIn automation class
├── linkedin_advanced.py        # Advanced features and methods
├── linkedin_scheduler.py       # Task scheduling system
├── example_usage.py           # Usage examples and demos
├── requirements.txt           # Python dependencies
├── env_example.txt           # Environment variables template
├── configuration/
│   └── login_credentials.py  # Legacy credential storage
└── README.md                 # This file
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password
LINKEDIN_2FA_SECRET=your_2fa_secret_if_available
```

### Browser Options

The automation supports both standard and undetected Chrome drivers:

```python
# Use undetected driver (recommended)
linkedin = AdvancedLinkedInAutomation(use_undetected=True)

# Use standard driver
linkedin = AdvancedLinkedInAutomation(use_undetected=False)

# Run in headless mode
linkedin = AdvancedLinkedInAutomation(headless=True)
```

## 📊 Available Methods

### Basic Operations

- `login()` - Login to LinkedIn
- `search_people(keywords, location, max_results)` - Search for people
- `connect_with_person(profile_url, message)` - Send connection request
- `post_content(content, image_path)` - Post content to feed
- `send_message(profile_url, message)` - Send message to connection

### Engagement

- `like_posts(max_likes)` - Like posts in feed
- `comment_on_posts(comments, max_comments)` - Comment on posts
- `accept_connection_requests(max_accepts)` - Accept pending requests

### Scheduling

- `add_daily_task(function, time, *args, **kwargs)` - Add daily recurring task
- `add_weekly_task(function, day, time, *args, **kwargs)` - Add weekly task
- `add_interval_task(function, minutes, *args, **kwargs)` - Add interval task

## ⚠️ Safety Guidelines

### Rate Limits

- **Connection Requests**: Max 100 per week
- **Messages**: Max 20 per day
- **Profile Views**: Max 50 per day
- **Posts**: Max 1-2 per day

### Best Practices

1. **Use Random Delays**: Built-in random delays between actions
2. **Vary Activities**: Don't repeat the same actions
3. **Human-like Behavior**: Random typing patterns and delays
4. **Monitor Account**: Watch for any restrictions
5. **Take Breaks**: Don't run automation 24/7
6. **Comply with ToS**: Always follow LinkedIn's Terms of Service

## 🚨 Important Notes

### Legal and Ethical Considerations

- This tool is for educational and personal use only
- Always comply with LinkedIn's Terms of Service
- Respect other users' privacy and preferences
- Use responsibly and don't spam or abuse the platform
- Consider using LinkedIn's official API when possible

### Detection Avoidance

- The tool uses undetected-chromedriver to minimize detection
- Random delays and human-like behavior patterns
- Built-in rate limiting to stay within safe limits
- Regular breaks and varied activity patterns

## 🐛 Troubleshooting

### Common Issues

1. **Login Failed**

   - Check credentials in `.env` file
   - Ensure 2FA is disabled or handle it manually
   - Try using undetected driver

2. **Element Not Found**

   - LinkedIn may have changed their UI
   - Update selectors in the code
   - Add more wait time

3. **Rate Limited**

   - Reduce automation frequency
   - Increase delays between actions
   - Take longer breaks

4. **Chrome Driver Issues**
   - Update Chrome browser
   - Clear browser cache
   - Try different driver options

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is for educational purposes only. Use at your own risk and always comply with LinkedIn's Terms of Service.

## ⚡ Quick Examples

### Search and Connect

```python
with AdvancedLinkedInAutomation() as linkedin:
    if linkedin.login():
        profiles = linkedin.search_people("data scientist", max_results=5)
        for profile in profiles:
            linkedin.connect_with_person(profile['profile_url'], "Hi! I'd like to connect.")
```

### Daily Automation

```python
scheduler = LinkedInScheduler()
linkedin = AdvancedLinkedInAutomation()

scheduler.add_daily_task(
    lambda: linkedin.like_posts(max_likes=5),
    "09:00"
)
scheduler.start()
```

### Content Posting

```python
with AdvancedLinkedInAutomation() as linkedin:
    if linkedin.login():
        linkedin.post_content("Excited to share my latest project! #coding #python")
```

## 📞 Support

For issues and questions:

1. Check the troubleshooting section
2. Review the code comments
3. Check LinkedIn's current UI for changes
4. Ensure you're following safety guidelines

---

**Disclaimer**: This tool is for educational purposes only. Users are responsible for complying with LinkedIn's Terms of Service and applicable laws. Use at your own risk.
#   L i n k e d I n - A u t o a p p l y  
 