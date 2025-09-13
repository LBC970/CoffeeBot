import json
import os
import random
import datetime
import boto3
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

# Initialize S3 client
s3 = boto3.client('s3')
BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
HISTORY_KEY = 'coffee_history.json'

# Initialize Slack app
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    process_before_response=True
)

# Initialize the Slack request handler for Lambda
SlackRequestHandler.clear_all_log_handlers()
slack_handler = SlackRequestHandler(app)


class CoffeePairingBot:
    def __init__(self):
        self.today = datetime.date.today().strftime("%Y-%m-%d")
        # Use test history file if in test mode
        self.history_key = 'test_history.json' if os.environ.get('TEST_MODE') == 'true' else HISTORY_KEY
        self.history = self.load_history()
    
    def load_history(self):
        """Load pairing history from S3"""
        try:
            response = s3.get_object(Bucket=BUCKET_NAME, Key=self.history_key)
            return json.loads(response['Body'].read().decode('utf-8'))
        except s3.exceptions.NoSuchKey:
            # First time running, create new history
            return {"pairings": []}
    
    def save_history(self):
        """Save pairing history to S3"""
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=self.history_key,
            Body=json.dumps(self.history, indent=2),
            ContentType='application/json'
        )
    
    def calculate_pairing_score(self, person1, person2):
        """
        Calculate a weighted penalty score for pairing two people.
        Higher score = better pairing (less recent, fewer total pairings)
        """
        today_date = datetime.datetime.strptime(self.today, "%Y-%m-%d").date()
        
        # Find all times these two people have been paired
        pairing_dates = []
        for pairing in reversed(self.history["pairings"]):
            for pair in pairing["pairs"]:
                if (person1 in pair and person2 in pair):
                    pairing_dates.append(pairing["date"])
        
        # If never paired, return maximum score
        if not pairing_dates:
            return 100
        
        # Find the most recent pairing
        most_recent_date_str = max(pairing_dates)
        most_recent_date = datetime.datetime.strptime(most_recent_date_str, "%Y-%m-%d").date()
        
        # Calculate days since last pairing
        days_since = (today_date - most_recent_date).days
        
        # Base score based on time since last pairing
        if days_since >= 180:  # 6+ months
            base_score = 50
        elif days_since >= 90:  # 3-6 months
            base_score = 20
        elif days_since >= 30:  # 1-3 months
            base_score = 5
        else:  # Less than 1 month
            base_score = 0
        
        # Penalty for multiple pairings (reduce score for each previous pairing)
        total_pairings = len(pairing_dates)
        repeat_penalty = (total_pairings - 1) * 10  # -10 points for each repeat
        
        final_score = max(0, base_score - repeat_penalty)
        
        # Debug logging
        print(f"Pairing score for {person1} + {person2}: {final_score} "
              f"(base: {base_score}, days: {days_since}, repeats: {total_pairings})")
        
        return final_score
    
    def get_last_single_date(self, person):
        """Find the most recent date when person was single (for single selection logic)"""
        for pairing in reversed(self.history["pairings"]):
            if pairing.get("single") == person:
                return pairing["date"]
        return "0000-00-00"  # Never been single
    
    def generate_pairings(self, participants):
        """Generate coffee pairings using weighted penalty scoring system"""
        random.shuffle(participants)  # Shuffle for initial randomness
        
        # Handle odd number of participants
        single_person = None
        if len(participants) % 2 != 0:
            # Find someone who has been single least recently or never
            single_candidates = participants.copy()
            single_candidates.sort(key=self.get_last_single_date)
            single_person = single_candidates[0]
            participants.remove(single_person)
        
        # Create best possible pairings using weighted scoring
        pairs = []
        unpaired = participants.copy()
        
        while len(unpaired) >= 2:
            best_pair = None
            best_score = -1  # Initialize with impossible score
            
            # Try all possible pairings and find the one with highest score
            for i in range(len(unpaired)):
                for j in range(i+1, len(unpaired)):
                    p1, p2 = unpaired[i], unpaired[j]
                    score = self.calculate_pairing_score(p1, p2)
                    
                    if score > best_score:
                        best_pair = [p1, p2]
                        best_score = score
            
            if best_pair:
                pairs.append(best_pair)
                unpaired.remove(best_pair[0])
                unpaired.remove(best_pair[1])
                print(f"Selected pair: {best_pair[0]} + {best_pair[1]} (score: {best_score})")
            else:
                # Fallback - should not happen with scoring system, but safety net
                pairs.append([unpaired[0], unpaired[1]])
                unpaired.remove(unpaired[0])
                unpaired.remove(unpaired[0])
                print(f"Fallback pairing used")
        
        # Save this week's pairings to history
        self.history["pairings"].append({
            "date": self.today,
            "pairs": pairs,
            "single": single_person
        })
        self.save_history()
        
        return pairs, single_person
    
    def format_output(self, pairs, single_person):
        """Format the pairings for Slack message"""
        output = f"*Coffee Pairings for {self.today}*\n"
        output += "=" * 40 + "\n\n"
        
        for i, pair in enumerate(pairs, 1):
            # Using <@user_id> format for proper Slack mentions
            output += f"*Pair {i}:* <@{pair[0]}> and <@{pair[1]}>\n"
        
        if single_person:
            output += "\n" + "=" * 40 + "\n"
            output += f"⭐ <@{single_person}> is without a partner this week.\n"
            output += "Please consider inviting them to join your coffee chat!\n"
        
        return output


# SLASH COMMAND HANDLERS
@app.command("/coffee-admin")
def handle_coffee_admin_command(ack, respond, command):
    """Handle /coffee-admin slash command"""
    ack()  # Acknowledge the command
    
    text = command.get('text', '').strip()
    parts = text.split() if text else []
    cmd = parts[0].lower() if parts else 'help'
    
    if cmd == 'help':
        respond({
            "response_type": "ephemeral",
            "text": "*Coffee Pairing Admin Commands*\n\n"
                   "`/coffee-admin help` - Show this help message\n"
                   "`/coffee-admin post-signup` - Post a new signup message\n"
                   "`/coffee-admin pair-now` - Run pairing algorithm immediately\n"
                   "`/coffee-admin status` - Show current signup status\n"
                   "`/coffee-admin delete-test` - Delete today's test messages\n"
                   "`/coffee-admin test-scoring` - Test the new scoring system"
        })
    
    elif cmd == 'post-signup':
        try:
            result = post_signup_message_internal()
            respond({
                "response_type": "ephemeral", 
                "text": f"✅ {result}"
            })
        except Exception as e:
            respond({
                "response_type": "ephemeral",
                "text": f"❌ Error posting signup message: {str(e)}"
            })
    
    elif cmd == 'pair-now':
        try:
            result = run_pairing_internal()
            respond({
                "response_type": "ephemeral",
                "text": f"✅ {result}"
            })
        except Exception as e:
            respond({
                "response_type": "ephemeral",
                "text": f"❌ Error running pairing: {str(e)}"
            })
    
    elif cmd == 'status':
        try:
            status_info = get_status_info()
            respond({
                "response_type": "ephemeral",
                "text": status_info
            })
        except Exception as e:
            respond({
                "response_type": "ephemeral",
                "text": f"❌ Error getting status: {str(e)}"
            })
    
    elif cmd == 'delete-test':
        try:
            result = delete_test_messages_internal()
            respond({
                "response_type": "ephemeral",
                "text": f"✅ {result}"
            })
        except Exception as e:
            respond({
                "response_type": "ephemeral",
                "text": f"❌ Error deleting messages: {str(e)}"
            })
    
    elif cmd == 'test-scoring':
        try:
            result = test_scoring_system()
            respond({
                "response_type": "ephemeral",
                "text": result
            })
        except Exception as e:
            respond({
                "response_type": "ephemeral",
                "text": f"❌ Error testing scoring: {str(e)}"
            })
    
    else:
        respond({
            "response_type": "ephemeral",
            "text": f"❌ Unknown command: `{cmd}`. Type `/coffee-admin help` for available commands."
        })


def test_scoring_system():
    """Test the new scoring system with some example pairs"""
    bot = CoffeePairingBot()
    
    # Test a few pairs from your history
    test_pairs = [
        ("Vinnie", "Nikhil Sripada"),  # Recently repeated
        ("AJ", "Gerard Kissane"),      # Old pairing
        ("Tom Winkles", "Jakob H"),    # Test a different pair
    ]
    
    results = []
    results.append("*Scoring System Test Results:*\n")
    
    for person1, person2 in test_pairs:
        score = bot.calculate_pairing_score(person1, person2)
        results.append(f"• {person1} + {person2}: Score = {score}")
    
    return "\n".join(results)


def get_status_info():
    """Get current status of signups and pairings"""
    channel = os.environ.get('SLACK_CHANNEL', 'virtual-coffee')
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    # Check if signup message exists
    signup_status = "No signup message posted"
    participant_count = 0
    
    try:
        message_key = 'test_signup_message.json' if os.environ.get('TEST_MODE') == 'true' else 'latest_signup_message.json'
        response = s3.get_object(Bucket=BUCKET_NAME, Key=message_key)
        message_info = json.loads(response['Body'].read().decode('utf-8'))
        
        signup_status = f"Signup message posted on {message_info.get('posted_date', 'unknown date')}"
        
        # Get current participants using ANY emoji reaction
        try:
            reactions = app.client.reactions_get(
                channel=message_info['channel'],
                timestamp=message_info['ts']
            )
            
            if 'message' in reactions and 'reactions' in reactions['message']:
                participants = set()  # Use set to avoid duplicates
                for reaction in reactions['message']['reactions']:
                    participants.update(reaction['users'])  # Any emoji
                participant_count = len(participants)  # Convert to count
        except Exception:
            pass
            
    except Exception:
        pass
    
    # Check if pairings were run today
    bot = CoffeePairingBot()
    pairing_status = "No pairings generated today"
    if bot.history["pairings"] and bot.history["pairings"][-1]["date"] == today:
        last_pairing = bot.history["pairings"][-1]
        pair_count = len(last_pairing["pairs"])
        single = "with 1 person without a partner" if last_pairing.get("single") else "with everyone paired"
        pairing_status = f"Pairings generated: {pair_count} pairs {single}"
    
    return f"*Coffee Chat Status for {today}*\n\n" \
           f"📍 {signup_status}\n" \
           f"👥 Current participants: {participant_count}\n" \
           f"☕ {pairing_status}\n\n" \
           f"Is pairing week: {'Yes' if is_pairing_week() else 'No'}\n\n" \
           f"🔧 *Using improved weighted penalty scoring system*\n" \
           f"🎯 *Accepts ANY emoji reactions for signup*"


# INTERNAL FUNCTIONS (called by both slash commands and scheduled events)
def post_signup_message_internal():
    """Internal function to post signup message"""
    channel = os.environ.get('SLACK_CHANNEL', 'virtual-coffee')
    today = datetime.date.today()
    
    try:
        # Check if we already posted today
        try:
            message_key = 'test_signup_message.json' if os.environ.get('TEST_MODE') == 'true' else 'latest_signup_message.json'
            response = s3.get_object(Bucket=BUCKET_NAME, Key=message_key)
            existing = json.loads(response['Body'].read().decode('utf-8'))
            if existing.get('posted_date') == today.strftime("%Y-%m-%d"):
                return f"Signup message already posted today ({today})"
        except s3.exceptions.NoSuchKey:
            pass
        
        # Post the signup message (simple coffee emoji instruction, but backend accepts any emoji)
        result = app.client.chat_postMessage(
            channel=channel,
            text="☕ Coffee Chat Signups - React to this message!",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🎯 *Coffee Chat Signups*\n<!here>\nAdd a ☕ reaction to this message by noon Wednesday to be paired for this week's coffee chats!"
                    }
                }
            ]
        )
        
        # Store the message timestamp in S3
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=message_key,
            Body=json.dumps({
                'ts': result['ts'],
                'channel': channel,
                'posted_date': today.strftime("%Y-%m-%d")
            }),
            ContentType='application/json'
        )
        
        return 'Signup message posted successfully'
        
    except Exception as e:
        raise Exception(f"Error posting signup message: {str(e)}")


def run_pairing_internal():
    """Internal function to run pairing algorithm - FIXED VERSION"""
    channel = os.environ.get('SLACK_CHANNEL', 'virtual-coffee')
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    try:
        # Check if we already ran pairings today
        bot = CoffeePairingBot()
        if bot.history["pairings"] and bot.history["pairings"][-1]["date"] == today:
            return f"Pairings already generated today ({today})"
        
        # Get the latest signup message info
        message_key = 'test_signup_message.json' if os.environ.get('TEST_MODE') == 'true' else 'latest_signup_message.json'
        response = s3.get_object(Bucket=BUCKET_NAME, Key=message_key)
        message_info = json.loads(response['Body'].read().decode('utf-8'))
        
        # Get reactions on the message
        reactions = app.client.reactions_get(
            channel=message_info['channel'],
            timestamp=message_info['ts']
        )
        
        # Get participants from ANY emoji reactions
        participants = set()
        if 'message' in reactions and 'reactions' in reactions['message']:
            for reaction in reactions['message']['reactions']:
                participants.update(reaction['users'])  # Any emoji
        
        participants = list(participants)  # Convert back to list
        
        if not participants:
            app.client.chat_postMessage(
                channel=channel,
                text="No one signed up for coffee chats this week! ☕"
            )
            return 'No participants found - posted notification'
        
        # CRITICAL FIX: Get user display names BEFORE generating pairings
        user_info = {}  # Maps user_id -> display_name
        participant_names = []  # List of display names for pairing algorithm
        
        for user_id in participants:
            try:
                user = app.client.users_info(user=user_id)
                display_name = user['user']['profile'].get('display_name') or user['user']['real_name']
                user_info[user_id] = display_name
                participant_names.append(display_name)  # Use display names for pairing
            except:
                # Fallback to user_id if API fails
                user_info[user_id] = user_id
                participant_names.append(user_id)
        
        # Generate pairings using DISPLAY NAMES (not user IDs) for consistency with history
        print(f"Generating pairings for {len(participant_names)} participants using weighted penalty system")
        print(f"Participants (display names): {participant_names}")
        
        # The bot's generate_pairings method will now work with display names
        # This ensures calculate_pairing_score can properly check history
        pairs_names, single_name = bot.generate_pairings(participant_names)
        
        # Now convert the paired display names back to user IDs for Slack mentions
        pairs_ids = []
        for pair_names in pairs_names:
            pair_ids = []
            for name in pair_names:
                # Find the user_id that corresponds to this display name
                for uid, uname in user_info.items():
                    if uname == name:
                        pair_ids.append(uid)
                        break
            if len(pair_ids) == 2:  # Only add if we found both IDs
                pairs_ids.append(pair_ids)
            else:
                print(f"Warning: Could not find user IDs for pair: {pair_names}")
        
        # Convert single person name back to ID for mention
        single_id = None
        if single_name:
            for uid, uname in user_info.items():
                if uname == single_name:
                    single_id = uid
                    break
        
        # Format output using user IDs for proper Slack mentions
        output = f"*Coffee Pairings for {today}*\n"
        output += "=" * 40 + "\n\n"
        
        for i, pair in enumerate(pairs_ids, 1):
            output += f"*Pair {i}:* <@{pair[0]}> and <@{pair[1]}>\n"
        
        if single_id:
            output += "\n" + "=" * 40 + "\n"
            output += f"⭐ <@{single_id}> is without a partner this week.\n"
            output += "Please consider inviting them to join your coffee chat!\n"
        
        # Post results
        app.client.chat_postMessage(
            channel=channel,
            text="☕ Coffee pairings are here!",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": output
                    }
                }
            ]
        )
        
        return f'Pairings generated successfully: {len(pairs_ids)} pairs (using improved scoring system with any emoji support)'
        
    except Exception as e:
        raise Exception(f"Error running pairing: {str(e)}")


def delete_test_messages_internal():
    """Internal function to delete test messages"""
    channel = os.environ.get('SLACK_CHANNEL', 'virtual-coffee')
    
    try:
        today = datetime.date.today().strftime("%Y-%m-%d")
        deleted_count = 0
        
        # Try to delete signup message
        try:
            response = s3.get_object(Bucket=BUCKET_NAME, Key='latest_signup_message.json')
            message_info = json.loads(response['Body'].read().decode('utf-8'))
            
            if message_info.get('posted_date') == today:
                app.client.chat_delete(
                    channel=message_info['channel'],
                    ts=message_info['ts']
                )
                deleted_count += 1
        except Exception as e:
            print(f"No signup message to delete: {e}")
        
        # Get recent messages to find pairing messages
        try:
            result = app.client.conversations_history(
                channel=channel,
                limit=20
            )
            
            for message in result['messages']:
                if (message.get('bot_id') and 
                    datetime.datetime.fromtimestamp(float(message['ts'])).date() == datetime.date.today()):
                    
                    if 'Coffee Pairings for' in message.get('text', '') or 'coffee pairings are here' in message.get('text', ''):
                        try:
                            app.client.chat_delete(
                                channel=channel,
                                ts=message['ts']
                            )
                            deleted_count += 1
                        except Exception:
                            pass
        except Exception:
            pass
        
        return f'Deleted {deleted_count} test messages from today'
        
    except Exception as e:
        raise Exception(f"Error in delete function: {str(e)}")


def is_pairing_week():
    """Determine if this is a pairing week based on a reference date"""
    ref_date_str = os.environ.get('REFERENCE_DATE', '2025-01-06')
    REFERENCE_DATE = datetime.datetime.strptime(ref_date_str, '%Y-%m-%d').date()
    
    today = datetime.date.today()
    days_diff = (today - REFERENCE_DATE).days
    weeks_diff = days_diff // 7
    
    return weeks_diff % 2 == 0


# SCHEDULED EVENT FUNCTIONS (original functions, now calling internal functions)
def post_signup_message(event, context):
    """Lambda function to post the signup message"""
    if not is_pairing_week():
        return {
            'statusCode': 200,
            'body': json.dumps('Not a scheduled week - skipping')
        }
    
    try:
        result = post_signup_message_internal()
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }


def run_pairing(event, context):
    """Lambda function to read reactions and create pairings"""
    if not is_pairing_week():
        return {
            'statusCode': 200,
            'body': json.dumps('Not a scheduled week - skipping')
        }
    
    try:
        result = run_pairing_internal()
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }


def delete_test_messages(event, context):
    """Lambda function to delete test messages"""
    try:
        result = delete_test_messages_internal()
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }


def delete_specific_message(event, context):
    """Delete a specific message by timestamp"""
    channel = os.environ.get('SLACK_CHANNEL', 'virtual-coffee')
    
    ts = event.get('timestamp')
    if not ts:
        return {
            'statusCode': 400,
            'body': json.dumps('Error: timestamp required')
        }
    
    try:
        app.client.chat_delete(
            channel=channel,
            ts=ts
        )
        return {
            'statusCode': 200,
            'body': json.dumps(f'Deleted message {ts}')
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }


# MAIN LAMBDA HANDLER
def lambda_handler(event, context):
    """Main Lambda handler that routes to appropriate function"""
    
    # Handle Slack requests (slash commands, interactions, events)
    if 'headers' in event and any(header.lower() in ['x-slack-signature', 'x-slack-request-timestamp'] 
                                 for header in event.get('headers', {})):
        return slack_handler.handle(event, context)
    
    # Handle scheduled EventBridge events
    if 'source' in event and event['source'] == 'aws.events':
        if event.get('action') == 'post_signup':
            return post_signup_message(event, context)
        elif event.get('action') == 'run_pairing':
            return run_pairing(event, context)
        elif event.get('action') == 'delete_test':
            return delete_test_messages(event, context)
        elif event.get('action') == 'delete_specific':
            return delete_specific_message(event, context)
    
    # Default behavior for testing
    return {
        'statusCode': 200,
        'body': json.dumps('Coffee bot is running with improved weighted penalty scoring and any emoji support!')
    }
