import os
from autogen import GroupChat, GroupChatManager, UserProxyAgent

# Import agent creation functions
from agents.ceo import create_ceo
from agents.creative_director import create_creative_director
from agents.media_buyer import create_media_buyer
from agents.copywriter import create_copywriter
from agents.art_director import create_art_director

# Import LLM config utility
from utils.llm_config import get_llm_config

# --- 1. Configuration and Agent Initialization ---
print("🤖 1. Loading configuration and initializing agents...")
llm_config = get_llm_config()

ceo = create_ceo(llm_config)
creative_director = create_creative_director(llm_config)
media_buyer = create_media_buyer(llm_config)
copywriter = create_copywriter(llm_config)
art_director = create_art_director(llm_config)

user_proxy = UserProxyAgent(
   name="HumanUser",
   human_input_mode="NEVER",
   max_consecutive_auto_reply=0,
   code_execution_config=False,
)

# --- 2. Define Campaign Inputs ---
print("📝 2. Defining campaign inputs...")
brand_info = "EcoWear, a sustainable fashion company for millennials."
target_users = "Environmentally conscious millennials (ages 25-40) who value transparency and style."
main_goal = "Increase online sales by 25% in the next quarter."
visual_identity = "Clean, earthy tones, natural imagery, and a modern, minimalist aesthetic."

initial_brief = (
    f"Team, here is the brief for our new campaign:\n"
    f"- **Brand:** {brand_info}\n"
    f"- **Target Audience:** {target_users}\n"
    f"- **Main Goal/KPI:** {main_goal}\n"
    f"- **Visual Identity:** {visual_identity}\n\n"
    "Let's collaboratively brainstorm to define 3 high-level marketing strategies. CEO, please facilitate and summarize the final list."
)

# --- 3. Phase 1: Strategy Meeting ---
print("\n🚀 3. Starting Phase 1: Strategy Meeting...")
strategy_group_chat = GroupChat(
    agents=[user_proxy, ceo, creative_director, media_buyer],
    messages=[],
    max_round=10,
    # FIX: Use round robin to ensure everyone speaks
)
strategy_manager = GroupChatManager(groupchat=strategy_group_chat, llm_config=llm_config)
user_proxy.initiate_chat(strategy_manager, message=initial_brief)

# FIX: A more reliable way to get the last message from a specific agent
def get_last_message_from(agent_name, group_chat):
    for msg in reversed(group_chat.messages):
        if msg['name'] == agent_name:
            return msg['content']
    return ""

strategy_result = get_last_message_from("CEO", strategy_group_chat).replace("TERMINATE", "").strip()
if not strategy_result:
    print("🛑 CEO did not provide strategies. Exiting.")
    exit()

print("\n✅ Phase 1 Complete. Final Strategies:")
print(strategy_result)

# --- 4. Phase 2: Creative Development & Review Loop ---
print("\n🎨 4. Starting Phase 2: Creative Development & Review Loop...")

approved = False
feedback = "This is the first brainstorming session. Please generate 3 distinct campaign ideas for each of the 3 strategies."
max_retries = 2
creative_ideas = ""

while not approved and max_retries > 0:
    print(f"\n--- Creative Round (Retries left: {max_retries}) ---")

    creative_task = (
        f"Creative Team, based on the approved strategies:\n\n{strategy_result}\n\n"
        f"Your task is to collaboratively generate 3 distinct campaign ideas for EACH of the 3 strategies (9 ideas total).\n"
        f"Feedback from previous round: {feedback}\n\n"
        "Copywriter and Art Director, please brainstorm together. Creative Director, please facilitate and then summarize the final 9 ideas in a single list."
    )

    creative_group_chat = GroupChat(
        agents=[user_proxy, creative_director, copywriter, art_director],
        messages=[],
        max_round=15,
        speaker_selection_method="round_robin" # FIX: Force collaboration
    )
    creative_manager = GroupChatManager(groupchat=creative_group_chat, llm_config=llm_config)
    user_proxy.initiate_chat(creative_manager, message=creative_task)

    creative_ideas = get_last_message_from("CreativeDirector", creative_group_chat).replace("TERMINATE", "").strip()
    if not creative_ideas:
        print("🛑 Creative Director did not provide a summary of ideas. Exiting.")
        exit()

    print("\n🧐 Creative Director reviewing the generated ideas...")

    review_task = (
        "Creative Director, you are now in review mode. "
        "Analyze the following 9 campaign ideas ALONE. "
        "Your response MUST start with either 'APPROVAL:' or 'REVISION_NEEDED:'. Do not add any other text before it.\n\n"
        f"Here are the ideas:\n{creative_ideas}"
    )

    # Use a direct chat for the review to avoid confusion
    review_response = creative_director.generate_reply(messages=[{"role": "user", "content": review_task}])
    cd_decision = review_response if isinstance(review_response, str) else str(review_response.get("content", ""))


    if cd_decision.strip().startswith("APPROVAL:"):
        approved = True
        print("\n✅ Creative concepts APPROVED.")
    else:
        feedback = cd_decision.replace("REVISION_NEEDED:", "").strip()
        print(f"\n❌ REVISION NEEDED. Feedback: {feedback}")
        max_retries -= 1

if not approved:
    print("\n🛑 Creative process failed to get approval after multiple revisions. Exiting.")
    exit()

# --- 5. Phase 3: Media Buyer Assessment ---
print("\n📊 5. Starting Phase 3: Media Buyer Assessment...")
assessment_task = (
    "Media Buyer, the creative team has finalized and received approval for the following campaign ideas. "
    "Please conduct your final assessment and provide a structured report.\n\n"
    f"Here are the approved concepts:\n{creative_ideas}"
)
# Using direct chat here too for simplicity and reliability
media_buyer_report_response = media_buyer.generate_reply(messages=[{"role": "user", "content": assessment_task}])
media_buyer_report = media_buyer_report_response if isinstance(media_buyer_report_response, str) else str(media_buyer_report_response.get("content", ""))
media_buyer_report = media_buyer_report.replace("TERMINATE", "").strip()
print("\n✅ Phase 3 Complete. Media Buyer's Report:")
print(media_buyer_report)

# --- 6. Phase 4: Final Summary Meeting ---
print("\n🤝 6. Starting Phase 4: Final Summary Meeting...")
summary_task = (
    "Team, we are in the final meeting. Our goal is to synthesize everything into a clear, final summary for the client.\n\n"
    f"**Initial Strategies:**\n{strategy_result}\n\n"
    f"**Media Buyer's Report:**\n{media_buyer_report}\n\n"
    "Please discuss and create a final, summarized action plan for each of the 3 strategies, incorporating the media plan. CEO, please provide the final conclusive summary."
)
summary_group_chat = GroupChat(
    agents=[user_proxy, ceo, creative_director, media_buyer],
    messages=[],
    max_round=10,
    speaker_selection_method="round_robin"
)
summary_manager = GroupChatManager(groupchat=summary_group_chat, llm_config=llm_config)
user_proxy.initiate_chat(summary_manager, message=summary_task)

final_summary = get_last_message_from("CEO", summary_group_chat).replace("TERMINATE", "").strip()
print("\n✅ Phase 4 Complete. Final Summarized Plan:")
print(final_summary)

# --- 7. Phase 5: Human Selection ---
print("\n🧑‍💻 7. Final Phase: Human Selection...")
print("The AI team has prepared the following 3 strategic options.")

final_choice = ""
while final_choice not in ["1", "2", "3"]:
    final_choice = input("Please review the final summary and choose the strategy to execute (1, 2, or 3): ")

print(f"\n🎉 Workflow Finished! You have selected strategy #{final_choice}. Now handing off to the execution team. 🎉")