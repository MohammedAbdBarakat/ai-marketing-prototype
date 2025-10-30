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
def is_termination_msg(content) -> bool:
    have_content = content.get("content", None) is not None
    if have_content and "terminate" in content.get("content", "").lower():
        return True
    return False

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
                    message=f"CEO, you will start the meeting. Here is the brief:\n\n{brief}"
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
                    "You are Isabelle, the Creative Director. Your mission is to SUPERVISE your team (Leo the Copywriter and Maria the Art Director) to generate **one APPROVED campaign idea for each of the 3 marketing strategies.**\n"
                    "**CRITICAL SUPERVISORY PROCESS TO FOLLOW:**\n"
                    "1. **Introduce the Goal:** Start by stating the goal for the current strategy (e.g., 'Team, let's focus on Strategy 1...')."
                    "2. **Observe the Brainstorm:** You MUST then wait and allow the Art Director and Copywriter to discuss and develop their idea. Let them talk back-and-forth freely. Do not interrupt their creative exchange."
                    
                    "3. **Review and Decide:** After they present a combined idea, you MUST review it. You have two options:"
                    "   - **If the idea is strong and meets the goal**, you will say 'Excellent, that's approved. Now let's move to the next strategy.' and then you will introduce the next strategy's goal."
                    "   - **If the idea is weak or needs refinement**, you MUST provide specific, constructive feedback and ask for a revision. For example: 'That's a good start, but it's missing X. Can you refine it to be more Y?' or 'I like the copy, but the visuals feel disconnected. Please rethink the visual direction.' You will then go back to step 2 (Observe the Brainstorm) for this same strategy."
                    
                    "4. **Repeat for all Strategies:** You will repeat this 'Introduce -> Observe -> Review' loop until you have one APPROVED idea for all three strategies."
                    
                    "5. **Final Report:** Once THREE ideas have been approved, your absolute final task is to write the summary report. Your final message MUST ONLY be a markdown report of the 3 approved ideas. Then, and only then, write TERMINATE."
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
                    "You are David, the Media Buyer. Your mission is to conduct a FINAL ASSESSMENT of the following creative work. "
                    "Your final output must be ONLY a markdown report with sections for each strategy. Then, write TERMINATE."
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