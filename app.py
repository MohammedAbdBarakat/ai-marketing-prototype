import streamlit as st
import time
from agents.ceo import create_ceo
from agents.creative_director import create_creative_director
from agents.media_buyer import create_media_buyer
from agents.copywriter import create_copywriter
from agents.art_director import create_art_director
from utils.llm_config import get_llm_config
from autogen import GroupChat, GroupChatManager, UserProxyAgent

# --- UI Configuration ---
st.set_page_config(layout="wide", page_title="AI Marketing Team")
st.title("🤖 AI Marketing Team Workflow v6.0 (Orchestrated)")

# --- Helper Functions ---
def display_chat_history(groupchat, phase_key):
    st.session_state[f"history_{phase_key}"] = groupchat.messages
    with st.expander("Show Conversation Details", expanded=True):
        for msg in st.session_state[f"history_{phase_key}"]:
            avatar = "👤" if msg['name'] == 'HumanUser' else "🤖"
            with st.chat_message(name=msg['name'], avatar=avatar):
                st.markdown(msg['content'])

def get_last_message_from(agent_name, group_chat):
    for msg in reversed(group_chat.messages):
        if msg['name'] == agent_name:
            return msg['content'].replace("TERMINATE", "").strip()
    return ""

# --- Agent Initialization ---
@st.cache_resource
def initialize_agents():
    llm_config = get_llm_config()
    return {
        "ceo": create_ceo(llm_config),
        "creative_director": create_creative_director(llm_config),
        "media_buyer": create_media_buyer(llm_config),
        "copywriter": create_copywriter(llm_config),
        "art_director": create_art_director(llm_config),
        "user_proxy": UserProxyAgent(
            name="HumanUser", 
            human_input_mode="NEVER", 
            max_consecutive_auto_reply=25,
            code_execution_config=False, 
            llm_config=llm_config
        ),
        "llm_config": llm_config
    }

agents = initialize_agents()
llm_config = agents['llm_config']

# --- State Management & Sidebar ---
if 'current_phase' not in st.session_state:
    st.session_state.current_phase = 0

with st.sidebar:
    st.header("Campaign Brief")
    brand_info = st.text_area("Brand Info", "EcoWear, a sustainable fashion company.")
    target_users = st.text_area("Target Audience", "Environmentally conscious millennials (25-40).")
    main_goal = st.text_area("Main Goal", "Increase online sales by 25%.")
    start_button = st.button("Start New Campaign")
    if start_button:
        st.session_state.clear()
        st.session_state.current_phase = 1
        st.rerun()

if st.session_state.current_phase == 0:
    st.info("Fill in the brief and click 'Start'.")

# --- Termination Function ---
def is_termination_msg(message) -> bool:
    """
    Checks if a message from a designated "leader" agent contains the word TERMINATE.
    """
    # Check if the message content exists and is a string
    content = message.get("content", "")
    if not isinstance(content, str):
        return False

    # Get the name of the agent who sent the message
    speaker_name = message.get("name")

    # Define a list of agents who are allowed to terminate a conversation
    # These are the agents responsible for summarizing and concluding a phase.
    allowed_terminators = ["CEO", "CreativeDirector", "MediaBuyer"]

    # Check if the speaker is in our allowed list
    is_allowed_terminator = speaker_name in allowed_terminators
    
    # Check if the message content contains the termination keyword
    has_terminate = "terminate" in content.lower()

    # The message is a termination message if both conditions are true
    return is_allowed_terminator and has_terminate



# === PHASE 1: STRATEGY MEETING ===
if st.session_state.current_phase >= 1:
    st.header("Phase 1: Strategy Generation")
    
    if 'strategies' not in st.session_state:
        if st.button("🚀 Run Phase 1: Strategy Generation"):
            with st.status("The senior team is in a strategy meeting...", expanded=True) as status:
                brief = f"**Campaign Brief:**\n- Brand: {brand_info}\n- Audience: {target_users}\n- Goal: {main_goal}"
                
                # --- SETUP THE GROUP CHAT FOR THE STRATEGY MEETING ---
                strategy_group_chat = GroupChat(
                    agents=[agents['ceo'], agents['creative_director'], agents['media_buyer']],
                    messages=[], 
                    max_round=40,
                    speaker_selection_method="round_robin" 
                )
                manager = GroupChatManager(
                    groupchat=strategy_group_chat, 
                    llm_config=llm_config, 
                    is_termination_msg=is_termination_msg
                )

                # --- START THE CONVERSATION ---
                # The CEO starts the meeting with the brief
                agents['user_proxy'].initiate_chat(
                manager,
                message=(
                    f"🧠 Phase 1: Strategic Alignment Meeting\n\n"
                    f"Here is the campaign brief:\n\n{brief}\n\n"
                    "Participants:\n"
                    "• Alex — CEO (meeting chairperson)\n"
                    "• Isabelle — Creative Director\n"
                    "• David — Media Buyer\n\n"
                    "🎯 **Goal:** Collaboratively develop exactly **three distinct and approved marketing strategies** "
                    "that align with the campaign brief.\n\n"
                    "💡 **Meeting Process:**\n"
                    "1. **Alex (CEO)** opens the meeting, presents the brief, and proposes the **first draft idea**.\n"
                    "2. **Isabelle (Creative Director)** then reacts from a creative and brand perspective — approve or reject and explain why.\n"
                    "3. **David (Media Buyer)** follows with a feasibility and performance assessment — approve or reject and explain why.\n"
                    "4. If either Isabelle or David rejects, Alex must refine the concept and restart that round until both approve.\n"
                    "5. Once both approve, Alex confirms the idea as **Strategy #N (Approved)** and starts the next round.\n"
                    "6. Repeat until three strategies are approved.\n"
                    "7. When all three are approved, Alex summarizes them as a clean, numbered list and then writes **TERMINATE** on a new line.\n\n"
                    "🗣️ **Guidelines:** Keep the discussion focused and realistic. Avoid unnecessary chatter. "
                    "Each message should clearly show the reasoning behind your approval or rejection. "
                    "The conversation ends only when Alex writes TERMINATE."
                )
            )


                # --- EXTRACT THE FINAL RESULT & DISPLAY HISTORY ---
                st.session_state.strategies = get_last_message_from("CEO", strategy_group_chat)
                display_chat_history(strategy_group_chat, "phase1") # Use our history function
                
                status.update(label="Strategy Meeting Complete!", state="complete")
            st.rerun()

    if 'strategies' in st.session_state:
        st.subheader("✅ Output: 3 Core Strategies")
        st.markdown(st.session_state.strategies)
        # Display the chat history for Phase 1 if it exists
        if 'history_phase1' in st.session_state:
            with st.expander("Show Strategy Meeting Details", expanded=False):
                for msg in st.session_state.history_phase1:
                    st.chat_message(name=msg['name']).markdown(msg['content'])


# === PHASE 2: CREATIVE DEVELOPMENT ===
if st.session_state.current_phase == 1 and 'strategies' in st.session_state:
    if st.button("➡️ Continue to Phase 2: Creative Development"):
        st.session_state.current_phase = 2
        st.rerun()

if st.session_state.current_phase >= 2:
    st.divider()
    st.header("Phase 2: Creative Development")

    if 'creative_report' not in st.session_state:
        if st.button("🎨 Run Phase 2: Creative Development"):
            with st.status("The creative team is brainstorming...", expanded=True) as status:
                cd_phase2_prompt = (
                    "🎨 Phase 2: Creative Development — Supervisory Brief\n\n"
                    "You are Isabelle, the Creative Director. You are supervising your team — "
                    "Leo (Copywriter) and Maria (Art Director) — to produce one approved campaign concept for each of the three strategies provided.\n\n"

                    "🎯 **Objective:** For each strategy, guide your team through a short, structured brainstorm that results in a finalized creative concept.\n\n"

                    "🧭 **Your Supervisory Process:**\n"
                    "1. **Introduce the current strategy** (e.g., 'Team, let’s focus on Strategy 1...').\n"
                    "2. **Observe the brainstorm** between Leo and Maria. Let them exchange at least two meaningful rounds of collaboration.\n"
                    "3. **Evaluate their combined idea:**\n"
                    "   - If strong, clearly approve it (e.g., 'Excellent, that’s approved. Let’s move on.').\n"
                    "   - If weak, provide specific feedback (what’s missing, tone, cohesion) and ask them to refine it.\n"
                    "4. **Repeat** until all three strategies have an approved campaign idea.\n\n"

                    "📘 **Final Task:**\n"
                    "When all three campaigns are approved, summarize them in a **clear markdown report** using this structure:\n"
                    "### Final Approved Campaign Ideas\n"
                    "- Strategy 1: <title> — <summary>\n"
                    "- Strategy 2: <title> — <summary>\n"
                    "- Strategy 3: <title> — <summary>\n\n"
                    "End your final message with the word **TERMINATE**."
                )

                agents['creative_director'].update_system_message(cd_phase2_prompt)

                creative_task = f"Creative Director, you will start the meeting. Here are the strategies:\n\n{st.session_state.strategies}"
                
                creative_group_chat = GroupChat(
                    agents=[agents['creative_director'], agents['copywriter'], agents['art_director']],
                    messages=[], 
                    max_round=40,
                    speaker_selection_method="auto"
                )
                manager = GroupChatManager(groupchat=creative_group_chat, llm_config=llm_config, is_termination_msg=is_termination_msg)
                agents['user_proxy'].initiate_chat(manager, message=creative_task)

                st.session_state.creative_report = get_last_message_from("CreativeDirector", creative_group_chat)
                display_chat_history(creative_group_chat, "phase2")
                status.update(label="Creative Development Complete!", state="complete")
            st.rerun()
            
    if 'creative_report' in st.session_state:
        st.subheader("✅ Output: 3 Campaign Ideas")
        st.markdown(st.session_state.creative_report)
        if 'history_phase2' in st.session_state:
            with st.expander("Show Conversation Details", expanded=True):
                for msg in st.session_state.history_phase2:
                    st.chat_message(name=msg['name']).markdown(msg['content'])

# === PHASE 3: FINAL ANALYSIS & SELECTION ===
if st.session_state.current_phase == 2 and 'creative_report' in st.session_state:
    if st.button("➡️ Continue to Phase 3: Final Analysis"):
        st.session_state.current_phase = 3
        st.rerun()

if st.session_state.current_phase >= 3:
    st.divider()
    st.header("Phase 3: Final Analysis")
    
    if 'media_report' not in st.session_state:
        if st.button("📊 Run Phase 3: Media Buyer Analysis"):
            with st.status("The Media Buyer is analyzing...", expanded=True) as status:
                mb_phase3_prompt = (
                    "📊 Phase 3: Final Media Analysis\n\n"
                    "You are David, the Media Buyer. You are evaluating the creative report provided by Isabelle and her team. "
                    "Your mission is to assess each campaign for **media feasibility, cost efficiency, and expected ROI**.\n\n"

                    "🧭 **Your Assessment Process:**\n"
                    "1. Review each strategy carefully.\n"
                    "2. For each, write a section titled `### Strategy X: <Title>`.\n"
                    "3. Inside each section, write three short parts:\n"
                    "   - **Strengths:** practical media and engagement advantages.\n"
                    "   - **Weaknesses:** risks or execution challenges.\n"
                    "   - **Recommendations:** specific improvements or next actions.\n\n"
                    "💡 Keep your tone analytical but collaborative — you’re guiding the team toward success, not criticizing.\n\n"
                    "Your final message must ONLY be a markdown report following that format. "
                    "End with the word **TERMINATE**."
                )

                agents['media_buyer'].update_system_message(mb_phase3_prompt)
                assessment_task = f"Media Buyer, here is the creative report for your analysis:\n\n{st.session_state.creative_report}"
                
                media_buyer_response = agents['media_buyer'].generate_reply(messages=[{"role": "user", "content": assessment_task}])
                st.session_state.media_report = media_buyer_response.replace("TERMINATE", "").strip()
                status.update(label="Analysis Complete!", state="complete")
            st.rerun()

    if 'media_report' in st.session_state:
        st.subheader("✅ Output: Media Buyer's Report")
        st.markdown(st.session_state.media_report)

        st.divider()
        st.header("🧑‍💻 Final Decision")
        st.info("Review the creative ideas and the media buyer's analysis to make your final decision.")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Creative Report")
            st.markdown(st.session_state.creative_report)
        with col2:
            st.subheader("Media Buyer Analysis")
            st.markdown(st.session_state.media_report)
        
        with st.form("selection_form"):
            final_choice = st.radio("Which strategy will you approve?", options=["Strategy 1", "Strategy 2", "Strategy 3"])
            submitted = st.form_submit_button("Confirm and Finalize Campaign")
            if submitted:
                st.session_state.final_choice = final_choice
        
        if 'final_choice' in st.session_state:
             st.success(f"🎉 Workflow Finished! You have approved **{st.session_state.final_choice}**. The campaign is ready for execution. 🎉")