import io
import re
import requests
import streamlit as st
from google import genai
from google.genai import types

# -----------------------------------------------------------------------------
# 1. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Franklin D. Roosevelt | Fireside Chat",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. Secure API Key
# -----------------------------------------------------------------------------
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("API Key Missing: Please configure `GEMINI_API_KEY` in Streamlit secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

# -----------------------------------------------------------------------------
# 3. Robust Server-Side Image Loader (Bypasses 403 Hotlinking Blocks)
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=86400)
def fetch_image_bytes(url: str):
    """
    Downloads image bytes on the server using an educational User-Agent.
    Prevents browser hotlink blocking (HTTP 403 Forbidden) from Wikimedia/NARA.
    """
    headers = {
        "User-Agent": "FDRHistoryClassroomBot/1.0 (Educational History Tool; contact@school.edu)"
    }
    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code == 200:
            return io.BytesIO(response.content)
    except Exception:
        pass
    return None

# -----------------------------------------------------------------------------
# 4. Verified Archival Visual Catalog
# -----------------------------------------------------------------------------
VISUAL_ARCHIVE = {
    "fireside_photo": {
        "title": "Photograph: FDR Delivering a Fireside Chat",
        "url": "https://upload.wikimedia.org/wikipedia/commons/5/51/FDR_Fireside_Chat_December_24%2C_1943.jpg",
        "caption": "President Roosevelt broadcasting to the American public over radio microphones. (FDR Presidential Library)",
        "trigger": "Use when discussing fireside chats, radio speeches, banking crisis, or speaking to the American people."
    },
    "dust_bowl_california": {
        "title": "Photograph: Migrant Mother, Nipomo, California (1936)",
        "url": "https://upload.wikimedia.org/wikipedia/commons/b/bc/Migrant_Mother_%28LOC_fsa.8b29516%29.jpg",
        "caption": "Dorothea Lange's iconic photograph of drought refugees in a California pea-pickers camp. (Library of Congress)",
        "trigger": "Use when discussing the Dust Bowl, Okies, farming collapse, or migration to California."
    },
    "tva_map": {
        "title": "Map: Tennessee Valley Authority Projects",
        "url": "https://upload.wikimedia.org/wikipedia/commons/e/eb/TVA-sites-map.png",
        "caption": "Regional development map of dams and public electrical power sites. (National Archives Catalog)",
        "trigger": "Use when discussing the TVA, dams, electricity, flood control, or regional development."
    },
    "ccc_workers": {
        "title": "Photograph: Civilian Conservation Corps Crew",
        "url": "https://upload.wikimedia.org/wikipedia/commons/7/7b/Photograph_of_Civilian_Conservation_Corps_%28CCC%29_Planting_Crew_-_NARA_-_2129004.jpg",
        "caption": "Young men planting pine seedlings to halt soil erosion under the New Deal. (National Archives Catalog)",
        "trigger": "Use when discussing the CCC, youth jobs, forestry, soil conservation, or relief programs."
    },
    "infamy_speech": {
        "title": "Document: Draft of the 'Day of Infamy' Address (Dec 8, 1941)",
        "url": "https://upload.wikimedia.org/wikipedia/commons/d/df/Day-of-infamy-draft1-page1.jpg",
        "caption": "FDR's annotated typed copy with handwritten edits declaring war on Japan. (National Archives / FDR Library)",
        "trigger": "Use when discussing Pearl Harbor, December 7, 1941, war declarations, or Congress."
    },
    "order_9066": {
        "title": "Document: Civilian Exclusion Order (Executive Order 9066)",
        "url": "https://upload.wikimedia.org/wikipedia/commons/0/02/Instructions_to_japanese.png",
        "caption": "Western Defense Command instructions posted in California ordering the relocation of Japanese Americans. (NARA)",
        "trigger": "Use when discussing Japanese American internment, Executive Order 9066, Manzanar, or Korematsu v. United States."
    },
    "pacific_theater_map": {
        "title": "Map: Pacific Ocean Theater of World War II",
        "url": "https://upload.wikimedia.org/wikipedia/commons/0/0a/Pacific_Area_-_World_War_II.jpg",
        "caption": "Allied Command operational zones in the Pacific war. (Office of the Historian, FRUS)",
        "trigger": "Use when discussing the Pacific war, Midway, island-hopping, or naval operations."
    }
}

# -----------------------------------------------------------------------------
# 5. System Instructions
# -----------------------------------------------------------------------------
image_triggers = "\n".join([f"- [IMAGE: {k}] -> {v['trigger']}" for k, v in VISUAL_ARCHIVE.items()])

SYSTEM_INSTRUCTION = f"""
You are Franklin Delano Roosevelt (FDR), 32nd President of the United States.
You are conversing with a California 10th-grade high school history student.

Voice & Reading Level:
1. Speak in your warm, reassuring fireside chat cadence ("My friends...", "Let us be clear...").
2. Match a 10th-grade reading level: clear, direct, articulate, and historically accurate.
3. Length: Strictly BETWEEN 15 AND 120 WORDS. Never speak fewer than 15 words and never exceed 120 words.

Historical Evidence & Citations:
1. Ground answers in primary sources: your letters, congressional legislation (CCC, TVA, Social Security, WPA), Supreme Court cases (Schechter Poultry, Korematsu), and presidential speeches.
2. Every answer MUST conclude with a source citation in parentheses at the end from one of these repositories:
   - (FDR Presidential Library & Museum, FRANKLIN Repository)
   - (Library of Congress, FDR Resource Guide)
   - (National Archives Catalog)
   - (The American Presidency Project, UC Santa Barbara)
   - (Foreign Relations of the United States, Office of the Historian)
   - (Eleanor Roosevelt Papers Project, GWU)
   - (Internet Archive, FDR Collections)
   - (FDR Library Museum Artifact Collection)

Visual Aids:
When discussing a topic with a matching photo or map, place the exact tag at the very end of your response:
{image_triggers}
Only include one tag when directly helpful.
"""

# -----------------------------------------------------------------------------
# 6. Memory & Session State
# -----------------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []

def display_media(image_key: str):
    """Safely loads and renders media bytes into the Streamlit chat."""
    if image_key and image_key in VISUAL_ARCHIVE:
        item = VISUAL_ARCHIVE[image_key]
        img_bytes = fetch_image_bytes(item["url"])
        if img_bytes:
            st.image(
                img_bytes,
                caption=f"{item['title']} — {item['caption']}",
                use_container_width=True
            )
        else:
            # Fallback if network drops
            st.caption(f"📁 **Archival Record**: [{item['title']}]({item['url']}) — {item['caption']}")

# -----------------------------------------------------------------------------
# 7. Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/FDR_1944_Color_Portrait.jpg/480px-FDR_1944_Color_Portrait.jpg",
        caption="Franklin D. Roosevelt (1882–1945)",
        use_container_width=True
    )
    st.title("FDR Fireside Desk")
    st.markdown("""
    **Audience**: California 10th Grade  
    **Model**: `gemini-3.5-flash-lite`  
    **Temperature**: `0.3`  
    **Memory Window**: 6 previous questions  
    **Length**: 15–120 words  
    """)
    if st.button("Reset Conversation", use_container_width=True):
        st.session_state.history = []
        st.rerun()

# -----------------------------------------------------------------------------
# 8. Chat Interface
# -----------------------------------------------------------------------------
st.title("🎙️ A Fireside Chat with FDR")
st.markdown("*Ask President Roosevelt about the New Deal, California in the 1930s, or World War II.*")

# Render previous turns
for turn in st.session_state.history:
    with st.chat_message("user"):
        st.markdown(turn["question"])
    with st.chat_message("assistant"):
        st.markdown(turn["clean_answer"])
        if turn.get("image_key"):
            display_media(turn["image_key"])

# Handle Input
user_input = st.chat_input("Ask Mr. President a question...")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    # Rolling memory: Last 5 turns + current question = 6 questions in context
    recent_turns = st.session_state.history[-5:]
    contents_payload = []
    for past in recent_turns:
        contents_payload.append(past["question"])
        contents_payload.append(past["raw_answer"])
    contents_payload.append(user_input)

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=contents_payload,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.3,
            )
        )
        raw_reply = response.text.strip()
    except Exception as e:
        raw_reply = f"My friends, the wireless communication has encountered a fault: {str(e)} (National Archives Catalog)"

    # Extract [IMAGE: key] tags
    image_match = re.search(r"\[IMAGE:\s*([a-zA-Z0-9_]+)\]", raw_reply)
    image_key = image_match.group(1) if image_match else None
    clean_reply = re.sub(r"\[IMAGE:\s*[a-zA-Z0-9_]+\]", "", raw_reply).strip()

    # Render response
    with st.chat_message("assistant"):
        st.markdown(clean_reply)
        if image_key:
            display_media(image_key)

    # Save to history
    st.session_state.history.append({
        "question": user_input,
        "raw_answer": raw_reply,
        "clean_answer": clean_reply,
        "image_key": image_key
    })

    # Keep memory capped at 6 questions
    if len(st.session_state.history) > 6:
        st.session_state.history = st.session_state.history[-6:]
