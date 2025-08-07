# ☕ Coffee Pairing Bot

An intelligent Slack bot that automatically pairs colleagues for coffee chats, fostering meaningful connections across your organization.

## 🌟 Features

- **Smart Pairing Algorithm**: Prioritizes new connections and avoids recent repeats using weighted penalty scoring
- **Slack Integration**: Seamless signup via emoji reactions and slash commands
- **Automated Scheduling**: Posts signup messages and generates pairings automatically
- **Historical Awareness**: Considers all past pairings to optimize future matches
- **Admin Controls**: Full control via slash commands for testing and management
- **Flexible Participation**: Handles odd numbers of participants gracefully
- **Data Persistence**: Stores pairing history and preferences in Amazon S3

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
- `/coffee-admin status` - Show current signup status
- `/coffee-admin delete-test` - Delete today's test messages
- `/coffee-admin test-scoring` - Test the scoring system

### User Workflow

1. **Signup**: Users react with ☕ emoji to signup messages
2. **Automatic Pairing**: System generates optimal pairings
3. **Notification**: Results posted to Slack with @mentions
4. **Coffee Chat**: Participants arrange their 30-minute chat

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

The bot uses a **weighted penalty scoring system**:

- **Never paired**: 100 points (highest priority)
- **6+ months ago**: 50 points
- **3-6 months ago**: 20 points
- **1-3 months ago**: 5 points
- **Recent pairings**: 0 points (avoided)
- **Repeat penalty**: -10 points per previous pairing

## 🔄 CI/CD Setup

### GitLab CI/CD

1. **Add CI/CD Variables** in GitLab:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_DEFAULT_REGION`

2. **Pipeline Configuration** (`.gitlab-ci.yml`):
   ```yaml
   stages:
     - test
     - deploy

   test:
     stage: test
     image: python:3.9
     script:
       - pip install -r requirements.txt
       - python -m pytest tests/

   deploy:
     stage: deploy
     image: python:3.9
     script:
       - ./deploy.sh
     only:
       - main
   ```

### Deployment Script

The `deploy.sh` script handles:
- Dependency installation
- Code packaging
- Lambda function updates
- Environment variable management

## 📁 Project Structure

```
coffee-pairing-bot/
├── src/
│   └── lambda_function.py          # Main Lambda function
├── tests/
│   └── test_pairing_algorithm.py   # Unit tests
├── scripts/
│   ├── deploy.sh                   # Deployment script
│   └── setup-infrastructure.sh     # AWS setup script
├── docs/
│   └── api.md                      # API documentation
├── .gitlab-ci.yml                  # CI/CD pipeline
├── requirements.txt                # Python dependencies
├── README.md                       # This file
└── LICENSE                         # License information
```

## 🛠️ Development

### Local Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/coffee-pairing-bot.git
   cd coffee-pairing-bot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up test environment**:
   ```bash
   export TEST_MODE=true
   export SLACK_BOT_TOKEN=your-test-token
   # ... other environment variables
   ```

4. **Run tests**:
   ```bash
   python -m pytest tests/
   ```

### Adding New Features

1. Create a feature branch: `git checkout -b feature/new-feature`
2. Make your changes
3. Add tests for new functionality
4. Update documentation
5. Submit a merge request

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
  ]
}
```

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
   - Verify emoji reaction name ("coffee")
   - Check message timestamp in S3
   - Confirm channel permissions

3. **Pairing algorithm issues**:
   - Use `/coffee-admin test-scoring` to debug
   - Check CloudWatch logs for scoring details
   - Verify name consistency in history

### Debug Commands

- `/coffee-admin status` - System health check
- `/coffee-admin test-scoring` - Algorithm testing
- Check CloudWatch logs for detailed execution traces

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Code Standards

- Follow PEP 8 for Python code style
- Add docstrings for all functions
- Include unit tests for new features
- Update documentation for user-facing changes

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♀️ Support

For issues and questions:

1. Check the [troubleshooting section](#-troubleshooting)
2. Search existing [GitHub Issues](https://github.com/your-org/coffee-pairing-bot/issues)
3. Create a new issue with:
   - Clear description of the problem
   - Steps to reproduce
   - CloudWatch logs (if applicable)
   - Environment details

## 🔮 Roadmap

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
