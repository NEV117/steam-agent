from utils.account_details import get_user_games 
from utils.scrape_steam_sales import scrape_steam_games 
import os
from dotenv import load_dotenv
from typing_extensions import Annotated
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager, LLMConfig
from flask import Flask, request, jsonify

# Flask application
app = Flask(__name__)

#---------------------------------------------------------------------------------------------------------------------
# Agent Prompts & Descriptions
#---------------------------------------------------------------------------------------------------------------------

STEAM_INFO_AGENT_PROMPT = """You are a Steam Data Specialist. Your task is to:
1. Call get_user_games_wrapper(user_id="string", count=100) to get the user's Steam games.
2. Call get_steam_sales_wrapper()
3. When both functions execute successfully, say EXACTLY: "I've gathered all the necessary data. I'll now pass control to recommendation_agent."
4. DO NOT try to analyze the data yourself or format it for the next agent."""

RECOMMENDATION_AGENT_PROMPT = """You are the Game Recommendation Agent. 
1. Read the previous messages to find user's games and current Steam sales Data.
2. Analyze this data to recommend 5 games based on:
   - Playtime patterns (priority)
   - Genre alignment 
   - Discount value (not that relevant)
3. Output analysis in this structure:
{
  "recommendations": [
    {
      "title": "Game Name", 
      "reason": "Concise justification",
      "price": "Current price",
      "discount": "Discount percentage",
    }
  ]
}"""

FORMATTER_AGENT_PROMPT = """You are the formatter_agent. Your tasks:
1. Find the recommendations from recommendation_agent in the chat history
2. Format them into markdown with the following format:
    ```Markdown
    # 🔥 Personalized Game Recommendations

        Here are some top picks just for you, based on your Steam library and current sales:

        {{#each recommendations}}
        ## 🎮 [{{title}}]({{steam_link}})
        ![{{title}}]({{image_url}})

        | Original Price | Discounted Price | You Save |
        |----------------|------------------|----------|
        | {{original_price}} | {{discounted_price}} | {{you_save}} |

        - **🔥 Discount:** {{discount}}  
        - **🎯 Why You'll Love It:**  
        {{reason}}

        ---
        {{/each}}

        💬 *Which one are you playing first? Let us know!*
    ```

3. After completing your task, add this EXACTLY on a new line:
\n\nTERMINATE

Example final output:
# Recommended Games\n\n... [markdown content] ... \n\nTERMINATE"""


#---------------------------------------------------------------------------------------------------------------------
# Function Registration 
#---------------------------------------------------------------------------------------------------------------------

load_dotenv()

# Configure AWS Bedrock LLM
llm_config = LLMConfig(
    api_type="bedrock",
    model="anthropic.claude-3-5-sonnet-20240620-v1:0",
    aws_region="us-east-1",
    aws_access_key=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_key=os.getenv("AWS_SECRET_KEY"),
    temperature=0.1,
    price=[0.003, 0.015],
    cache_seed=None,
)


# Create User Proxy for function execution
user_proxy = UserProxyAgent(
    name="Code_Executor",
    human_input_mode="NEVER",
    system_message="""You are the system coordinator. Your ONLY responsibilities are:
    1. Execute function calls when requested
    2. Return FULL function outputs verbatim
    3. Never modify or summarize results""",
    code_execution_config=False,
)

#---------------------------------------------------------------------------------------------------------------------
# Agent Configuration
#---------------------------------------------------------------------------------------------------------------------

steam_info_agent = AssistantAgent(
    name="steam_info_agent",
    system_message=STEAM_INFO_AGENT_PROMPT,
    llm_config=llm_config,
    is_termination_msg=lambda x: "TERMINATE" in (x.get("content", "") or "").upper(),
)

recommendation_agent = AssistantAgent(
    name="recommendation_agent",
    system_message=RECOMMENDATION_AGENT_PROMPT,
    llm_config=llm_config,
    is_termination_msg=lambda x: "TERMINATE" in (x.get("content", "") or "").upper(),
)

formatter_agent = AssistantAgent(
    name="formatter_agent",
    system_message=FORMATTER_AGENT_PROMPT,
    llm_config=llm_config,
    is_termination_msg=lambda x: "TERMINATE" in (x.get("content", "") or "").upper(),
)


# Register functions with proper signatures
@user_proxy.register_for_execution()
@steam_info_agent.register_for_llm(description="Get user's Steam games")
def get_user_games_wrapper (
    user_id: Annotated[str, "SteamID64 (decimal format)"],
    count: Annotated[int, "Number of games to return (1-100)"] = 10
) -> list[dict]:
    """Direct passthrough to Steam API wrapper"""
    return get_user_games(user_id=user_id, count=count)

@user_proxy.register_for_execution()
@steam_info_agent.register_for_llm(description="Get current Steam sales")
def get_steam_sales_wrapper() -> list[dict]:
    """Direct passthrough to sales scraper"""
    return scrape_steam_games()


#---------------------------------------------------------------------------------------------------------------------
# Enhanced Group Chat Setup
#---------------------------------------------------------------------------------------------------------------------

def custom_speaker_selection(last_speaker, group_chat):
    messages = group_chat.messages
    
    # If the latest message has the termination phrase, stop further agent selection.
    if messages and "TERMINATE" in messages[-1]["content"].upper():
        return None

    # If last message is from steam_info_agent and contains the trigger phrase
    if last_speaker == steam_info_agent and "I've gathered all the necessary data" in messages[-1]["content"]:
        return recommendation_agent
    
    # If last message is from recommendation_agent
    if last_speaker == recommendation_agent:
        return formatter_agent
    
    # Default to the steam_info_agent first
    if last_speaker == user_proxy and len(messages) <= 2:
        return steam_info_agent
        
    # Default to round-robin otherwise
    return "round_robin"

# Update your GroupChat configuration:
group_chat = GroupChat(
    agents=[user_proxy, steam_info_agent, recommendation_agent, formatter_agent],
    messages=[],
    max_round=15,
    speaker_selection_method=custom_speaker_selection
)

manager = GroupChatManager(groupchat=group_chat, llm_config=llm_config)

#---------------------------------------------------------------------------------------------------------------------
# Execution
# Steam_ID's to test:
# 76561198447564163 //NEV
# 76561198197414790 //JP 
# 76561198432852062 //Legarda
# 76561198147285117 //Collan
# 76561198975018370 //Meneses
# 76561199080812070 //Zerox
#---------------------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------------------
# Flask Routes
#---------------------------------------------------------------------------------------------------------------------

@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    # Get steam_id from query parameters
    steam_id = request.args.get('steam_id')

    # Get count parameter with default value of 10
    count = request.args.get('count', default=10, type=int)
    
    if not steam_id:
        return jsonify({'error': 'Missing steam_id parameter'}), 400
    
    try:
        # Include count in the message to be passed to the agents
        result = user_proxy.initiate_chat(
            manager,
            message=f"Generate Steam recommendations for user {steam_id} with count {count}",
            clear_history=True
        )
        
        # Extract the formatted recommendations from the last formatter_agent message
        markdown_output = None
        for message in reversed(manager.groupchat.messages):
            if message.get('name') == 'formatter_agent' and 'TERMINATE' in message.get('content', ''):
                content = message.get('content', '').replace('TERMINATE', '').strip()
                
                # Wrap the content in a markdown code block
                markdown_output = f"```Markdown\n{content}\n```"
                break
        
        if markdown_output:
            return jsonify({'success': True, 'markdown': markdown_output})
        else:
            return jsonify({'error': 'No recommendations generated'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#---------------------------------------------------------------------------------------------------------------------
# Main entry point
#---------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)