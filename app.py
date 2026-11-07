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
# 2. Secure API Key Management
# -----------------------------------------------------------------------------
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Missing Gemini API Key. Please add `GEMINI_API_KEY` to your Streamlit secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

# -----------------------------------------------------------------------------
# 3. Server-Side Image Fetcher (Guarantees pictures load directly from memory)
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=86400)
def get_image_data(url: str):
    """
    Downloads raw image bytes on the server using standard headers.
    Serving bytes directly via Streamlit eliminates browser 403 and CORS errors.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.content
    except Exception:
        pass
    return None

# -----------------------------------------------------------------------------
# 4. Verified Archival Visual Catalog (Direct, un-thumbnailed file links)
# -----------------------------------------------------------------------------
VISUAL_ARCHIVE = {
    "tva_map": {
        "title": "Historical Map: Tennessee Valley Authority Regional Dams",
        "url": "https://upload.wikimedia.org/wikipedia/commons/e/eb/TVA-sites-map.png",
        "caption": "Map of the public power and dam network created by the TVA Act. (National Archives Catalog)",
        "keywords": ["tva", "tennessee valley", "dam", "dams", "rural electrification", "public power"]
    },
    "dust_bowl_california": {
        "title": "Photograph: Migrant Mother in Nipomo, California (1936)",
        "url": "https://upload.wikimedia.org/wikipedia/commons/b/bc/Migrant_Mother_%28LOC_fsa.8b29516%29.jpg",
        "caption": "Drought refugees arriving in California's Central Valley. (Dorothea Lange / Library of Congress)",
        "keywords": ["dust bowl", "okie", "okies", "california", "drought", "farming", "migrant", "pea-picker"]
    },
    "order_9066": {
        "title": "Archival Document: Civilian Exclusion Order (Executive Order 9066)",
        "url": "https://upload.wikimedia.org/wikipedia/commons/0/02/Instructions_to_japanese.png",
        "caption": "Wartime Civil Control Administration notice posted in California ordering Japanese American removal. (National Archives Catalog)",
        "keywords": ["9066", "internment", "japanese", "manzanar", "exclusion", "relocation", "korematsu"]
    },
    "infamy_speech": {
        "title": "Archival Document: Annotated 'Day of Infamy' Address (Dec 8, 1941)",
        "url": "https://upload.wikimedia.org/wikipedia/commons/d/df/Day-of-infamy-draft1-page1.jpg",
        "caption": "FDR's handwritten revisions requesting Congress declare war on Japan. (FDR Presidential Library / FRANKLIN)",
        "keywords": ["pearl harbor", "infamy", "december 7", "declaration of war", "hawaii"]
    },
    "ccc_workers": {
        "title": "Photograph: Civilian Conservation Corps Planting Crew",
        "url": "https://upload.wikimedia.org/wikipedia/commons/7/7b/Photograph_of_Civilian_Conservation_Corps_%28CCC%29_Planting_Crew_-_NARA_-_2129004.jpg",
        "caption": "Young men planting trees to halt topsoil erosion and build state and national parks. (National Archives Catalog)",
        "keywords": ["ccc", "civilian conservation", "planting", "forestry", "trees", "erosion", "work camp"]
    },
    "fireside_photo": {
        "title": "Photograph: FDR Delivering an Address to the Nation",
        "url": "https://upload.wikimedia.org/wikipedia/commons/0/0a/Fdr_delivers_speech.jpg",
        "caption": "President Roosevelt addressing Congress and the nation. (FDR Presidential Library)",
        "keywords": ["fireside", "radio", "broadcast", "bank holiday", "hundred days", "speech", "address"]
    },
    "pacific_theater_map": {
        "title": "Military Map: Pacific Ocean Theater of World War II",
        "url": "https://upload.wikimedia.org/wikipedia/commons/0/0a/Pacific_Area_-_World_War_II.jpg",
        "caption": "Allied Command operational boundaries across the Pacific theater. (Office of the Historian, FRUS)",
        "keywords": ["pacific", "midway", "island hopping", "nimitz", "macarthur", "navy", "fleet"]
    }
}

def identify_visual_key(tag_match: str, text_corpus: str) -> str:
    """Detects visual primary sources via Gemini tag or automated keyword matching."""
    if tag_match and tag_match in VISUAL_ARCHIVE:
        return tag_match
    lower_text = text_corpus.lower()
    for key, data in VISUAL_ARCHIVE.items():
        if any(kw in lower_text for kw in data["keywords"]):
            return key
    return None

# -----------------------------------------------------------------------------
# 5. FDR System Prompt
# -----------------------------------------------------------------------------
SYSTEM_INSTRUCTION = """
You are Franklin Delano Roosevelt (FDR), 32nd President of the United States.
You are conversing with a California 10th-grade high school history student.

Voice & Reading Level:
1. Speak in your warm, reassuring fireside chat cadence ("My friends...", "Let us be clear...").
2. Match a 10th-grade reading level: clear, direct, and historically grounded without archaic Victorian phrases.
3. Length: Strictly BETWEEN 15 AND 120 WORDS. Never speak fewer than 15 words and never exceed 120 words.

Historical Evidence & Source Grounding:
1. Base your knowledge strictly on primary sources: your letters, congressional legislation (CCC, TVA, Social Security, WPA), Supreme Court cases (Schechter Poultry, Korematsu), and presidential speeches.
2. Every answer MUST conclude with an explicit archival source citation in parentheses at the very end from one of these repositories:
   - (FDR Presidential Library & Museum, FRANKLIN Repository)
   - (Library of Congress, FDR Resource Guide)
   - (National Archives Catalog)
   - (The American Presidency Project, UC Santa Barbara)
   - (Foreign Relations of the United States, Office of the Historian)
   - (Eleanor Roosevelt Papers Project, GWU)
   - (Internet Archive, FDR Collections)
   - (FDR Library Museum Artifact Collection)

Visual Aids:
When discussing a relevant topic, place one tag at the very end of your response:
- [IMAGE: tva_map]
- [IMAGE: dust_bowl_california]
- [IMAGE: order_9066]
- [IMAGE: infamy_speech]
- [IMAGE: ccc_workers]
- [IMAGE: fireside_photo]
- [IMAGE: pacific_theater_map]
"""

# -----------------------------------------------------------------------------
# 6. Session State (Last 6 Questions Retained)
# -----------------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []

def render_artifact(image_key: str):
    """Fetches bytes from cache and renders the image directly inside Streamlit."""
    if image_key and image_key in VISUAL_ARCHIVE:
        item = VISUAL_ARCHIVE[image_key]
        img_bytes = get_image_data(item["url"])
        if img_bytes:
            st.image(
                img_bytes,
                caption=f"🏛️ {item['title']} — {item['caption']}",
                use_container_width=True
            )
        else:
            # Direct link fallback
            st.markdown(f"🏛️ **[{item['title']}]({item['url']})** — {item['caption']}")

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
    **Length**: 15–120 words  
    **Memory**: Last 6 questions retained  
    """)
    st.divider()
    if st.button("Reset Wire / Start Over", use_container_width=True):
        st.session_state.history = []
        st.rerun()

# -----------------------------------------------------------------------------
# 8. Main Chat Interface
# -----------------------------------------------------------------------------
st.title("🎙️ A Fireside Chat with FDR")
st.markdown("*Ask President Roosevelt about the New Deal, California in the Great Depression, or World War II.*")

# Replay conversation history
for turn in st.session_state.history:
    with st.chat_message("user"):
        st.markdown(turn["question"])
    with st.chat_message("assistant"):
        st.markdown(turn["clean_answer"])
        if turn.get("image_key"):
            render_artifact(turn["image_key"])

# Process input
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

    # Query Gemini 3.5 Flash-Lite
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

    # Identify image tag or topic
    match = re.search(r"\[IMAGE:\s*([a-zA-Z0-9_]+)\]", raw_reply)
    tag_key = match.group(1) if match else None
    image_key = identify_visual_key(tag_key, user_input + " " + raw_reply)

    # Clean raw tag out of the spoken text
    clean_reply = re.sub(r"\[IMAGE:\s*[a-zA-Z0-9_]+\]", "", raw_reply).strip()

    # Display Assistant response and verified image bytes
    with st.chat_message("assistant"):
        st.markdown(clean_reply)
        if image_key:
            render_artifact(image_key)

    # Store turn
    st.session_state.history.append({
        "question": user_input,
        "raw_answer": raw_reply,
        "clean_answer": clean_reply,
        "image_key": image_key
    })

    # Keep memory capped at 6 questions
    if len(st.session_state.history) > 6:
        st.session_state.history = st.session_state.history[-6:]
