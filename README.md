# ☕ Coffee Pairing Bot

An intelligent Slack bot that automatically pairs colleagues for coffee chats, fostering meaningful connections across your organization.

## 🌟 Features

- **Smart Pairing Algorithm**: Prioritizes new connections and avoids recent repeats using weighted penalty scoring
- **Badge System**: Track participation milestones with 6 badge levels (☕ → 🥉 → 🥈 → ⭐ → 🏅 → 🏆)
- **Veteran-Newcomer Pairing**: Intelligently pairs newcomers with experienced participants when possible
- **Slack Integration**: Seamless signup via emoji reactions and slash commands
- **Automated Scheduling**: Posts signup messages and generates pairings automatically
- **Historical Awareness**: Considers all past pairings to optimize future matches
- **Admin Controls**: Full control via slash commands for testing and management
- **Flexible Participation**: Handles odd numbers of participants gracefully
- **Data Persistence**: Stores pairing history and badges in Amazon S3

## 🏗️ Architecture

```
Slack App ←→ AWS Lambda ←→ Amazon S3
    ↓              ↓
 Users        EventBridge
             (Scheduling)
```

### Components

- **AWS Lambda**: Core pairing logic and Slack integration
- **Amazon S3**: Persistent storage for pairing history
- **Slack App**: User interface and notifications
- **Amazon EventBridge**: Automated scheduling (optional)
- **GitLab CI/CD**: Automated deployments

## 📋 Prerequisites

- AWS Account with appropriate permissions
- Slack workspace with admin access
- Python 3.9+
- GitLab account (for CI/CD)
- Basic knowledge of AWS Lambda and Slack apps

## 🚀 Quick Start

### 1. Slack App Setup

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Create a new app "From scratch"
3. Configure the app with these scopes:
   ```
   Bot Token Scopes:
   - channels:history
   - channels:read
   - chat:write
   - commands
   - reactions:read
   - users:read
   - users:read.email
   ```
4. Add slash command `/coffee-admin`
5. Install the app to your workspace

### 2. AWS Infrastructure Setup

1. **Create S3 Bucket**:
   ```bash
   aws s3 mb s3://your-coffee-pairing-bucket
   ```

2. **Create Lambda Function**:
   ```bash
   aws lambda create-function \
     --function-name coffee-pairing-bot \
     --runtime python3.9 \
     --role arn:aws:iam::ACCOUNT:role/lambda-execution-role \
     --handler lambda_function.lambda_handler \
     --zip-file fileb://deployment.zip
   ```

3. **Set Environment Variables**:
   ```bash
   aws lambda update-function-configuration \
     --function-name coffee-pairing-bot \
     --environment Variables='{
       "SLACK_BOT_TOKEN": "xoxb-your-bot-token",
       "SLACK_SIGNING_SECRET": "your-signing-secret",
       "S3_BUCKET_NAME": "your-coffee-pairing-bucket",
       "SLACK_CHANNEL": "virtual-coffee",
       "REFERENCE_DATE": "2025-01-06"
     }'
   ```

### 3. Deploy the Code

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Deploy using the provided scripts or CI/CD pipeline

## 💻 Usage

### Admin Commands

All admin functionality is available through the `/coffee-admin` slash command:

- `/coffee-admin help` - Show available commands
- `/coffee-admin post-signup` - Post a signup message
- `/coffee-admin pair-now` - Generate pairings immediately
- `/coffee-admin status` - Show current signup status and badge distribution
- `/coffee-admin badges` - View badge levels for all participants
- `/coffee-admin delete-test` - Delete today's test messages
- `/coffee-admin test-scoring` - Test the scoring system

### User Workflow

1. **Signup**: Users react with any emoji to signup messages
2. **Automatic Pairing**: System generates optimal pairings with veteran-newcomer preference
3. **Notification**: Results posted to Slack with @mentions and badge level-ups
4. **Coffee Chat**: Participants arrange their 30-minute chat
5. **Badge Progress**: Earn badges as you participate (First Timer → Coffee Newbie → Regular → Coffee Enthusiast → Coffee Veteran → Coffee Legend)

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `SLACK_BOT_TOKEN` | Slack Bot User OAuth Token | Yes | - |
| `SLACK_SIGNING_SECRET` | Slack request verification | Yes | - |
| `S3_BUCKET_NAME` | S3 bucket for data storage | Yes | - |
| `SLACK_CHANNEL` | Channel for announcements | Yes | - |
| `REFERENCE_DATE` | Reference date for bi-weekly scheduling | No | `2025-01-06` |
| `TEST_MODE` | Use test data files | No | `false` |

### Pairing Algorithm

The bot uses a **weighted penalty scoring system** with veteran-newcomer preference:

**Scoring System:**
- **Never paired**: 100 points (highest priority)
- **6+ months ago**: 50 points
- **3-6 months ago**: 20 points
- **1-3 months ago**: 5 points
- **Recent pairings**: 0 points (avoided)
- **Repeat penalty**: -10 points per previous pairing

**Veteran-Newcomer Pairing:**
- Newcomers (≤3 participations) are preferentially paired with veterans (≥8 participations)
- Only applied when pairing score > 10 to maintain repeat avoidance priority
- Helps onboard new participants with experienced coffee chatters

**Badge Levels:**
- ☕ **First Timer** (1 participation)
- 🥉 **Coffee Newbie** (2-3 participations)
- 🥈 **Regular** (4-7 participations)
- ⭐ **Coffee Enthusiast** (8-11 participations)
- 🏅 **Coffee Veteran** (12-15 participations)
- 🏆 **Coffee Legend** (16+ participations)

**Badge Update Display:**
When participants earn new badges, they're displayed grouped by level in descending order (Legend → Newbie):
```
🥉 Badge Updates:
🏆 Coffee Legend: Alice (16 chats), Bob (16 chats)
🥈 Regular: Carol (4 chats)
```

## 🚀 Deployment

### Manual Deployment

The `scripts/deploy.sh` script handles:
- Dependency installation
- Code packaging into `deployment.zip`
- Lambda function updates via AWS CLI
- Environment variable management

Run deployment:
```bash
./scripts/deploy.sh
```

Ensure you have AWS credentials configured:
```bash
aws configure
# or set environment variables:
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_DEFAULT_REGION=us-east-1
```

## 📁 Project Structure

```
CoffeeBot/
├── src/
│   └── lambda_function.py          # Main Lambda function with all bot logic
├── scripts/
│   └── deploy.sh                   # Deployment script
├── examples/
│   ├── slack-app-manifest.json     # Slack app configuration template
│   └── sample_coffee_history.json  # Sample data structure
├── requirements.txt                # Python dependencies
├── README.md                       # This file
└── LICENSE                         # License information
```

## 🛠️ Development

### Local Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/LBC970/CoffeeBot.git
   cd CoffeeBot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up test environment**:
   ```bash
   export TEST_MODE=true
   export SLACK_BOT_TOKEN=your-test-token
   export SLACK_SIGNING_SECRET=your-signing-secret
   export S3_BUCKET_NAME=your-test-bucket
   export SLACK_CHANNEL=test-channel
   ```

4. **Test locally** (requires AWS credentials):
   ```bash
   python src/lambda_function.py
   ```

### Adding New Features

1. Create a feature branch: `git checkout -b feature/new-feature`
2. Make your changes
3. Test thoroughly in TEST_MODE
4. Update documentation as needed
5. Submit a pull request

## 📊 Monitoring and Maintenance

### CloudWatch Logs

Monitor Lambda execution through CloudWatch:
- Function errors and performance
- Pairing algorithm decisions
- Slack API interactions

### S3 Data Structure

```json
{
  "pairings": [
    {
      "date": "2025-07-16",
      "pairs": [
        ["User1", "User2"],
        ["User3", "User4"]
      ],
      "single": "User5"
    }
  ],
  "badges": {
    "User1": {
      "level": "Coffee Legend",
      "total_participations": 16
    },
    "User2": {
      "level": "Coffee Enthusiast",
      "total_participations": 10
    }
  }
}
```

The badge system automatically initializes from historical pairing data on first deployment.

### Regular Maintenance

- **Monthly**: Review pairing history for data quality
- **Quarterly**: Update dependencies and security patches
- **As needed**: Adjust scoring weights based on feedback

## 🐛 Troubleshooting

### Common Issues

1. **Slash commands not working**:
   - Check API Gateway configuration
   - Verify Lambda permissions
   - Confirm request URL in Slack app

2. **No participants found**:
   - Verify signup message exists and reactions are being captured
   - Check message timestamp is correctly stored in S3
   - Confirm bot has channel permissions and can read reactions

3. **Pairing algorithm issues**:
   - Use `/coffee-admin test-scoring` to debug
   - Check CloudWatch logs for scoring details
   - Verify name consistency in history

### Debug Commands

- `/coffee-admin status` - System health check and badge distribution
- `/coffee-admin badges` - View all participant badge levels
- `/coffee-admin test-scoring` - Algorithm testing
- Check CloudWatch logs for detailed execution traces

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Test changes thoroughly in TEST_MODE
4. Update documentation as needed
5. Submit a pull request

### Code Standards

- Follow PEP 8 for Python code style
- Add docstrings for all functions
- Test changes thoroughly in TEST_MODE before deploying
- Update documentation for user-facing changes

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♀️ Support

For issues and questions:

1. Check the [troubleshooting section](#-troubleshooting)
2. Search existing [GitHub Issues](https://github.com/LBC970/CoffeeBot/issues)
3. Create a new issue with:
   - Clear description of the problem
   - Steps to reproduce
   - CloudWatch logs (if applicable)
   - Environment details

## 🔮 Roadmap

Completed features:
- [x] Badge system for tracking participation milestones
- [x] Veteran-newcomer pairing preference

Planned features:
- [ ] Slack interactive buttons for signup
- [ ] Persistent user preferences (skip weeks, frequency)
- [ ] Analytics dashboard
- [ ] Integration with calendar systems
- [ ] Custom scoring weights per organization
- [ ] Multi-workspace support

## 🙏 Acknowledgments

- Slack Bolt framework for Python
- AWS Lambda for serverless execution
- The coffee culture that brings teams together ☕

---

**Made with ☕ and ❤️ for better team connections**
