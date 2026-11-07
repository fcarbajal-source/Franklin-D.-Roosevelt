import re
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
# 3. Primary Source Visual Catalog (Routed via Global CDN to avoid 403 blocks)
# -----------------------------------------------------------------------------
VISUAL_ARCHIVE = {
    "tva_map": {
        "title": "Historical Map: Tennessee Valley Authority Regional Dams",
        "cdn_url": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/thumb/e/eb/TVA-sites-map.png/800px-TVA-sites-map.png&output=jpg",
        "caption": "Map of the public power and dam network created by the TVA Act. (National Archives Catalog)",
        "keywords": ["tva", "tennessee valley", "dam", "dams", "rural electrification", "public power"]
    },
    "dust_bowl_california": {
        "title": "Photograph: Migrant Mother in Nipomo, California (1936)",
        "cdn_url": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/thumb/b/bc/Migrant_Mother_%28LOC_fsa.8b29516%29.jpg/800px-Migrant_Mother_%28LOC_fsa.8b29516%29.jpg&output=jpg",
        "caption": "Drought refugees arriving in California's Central Valley. (Dorothea Lange / Library of Congress)",
        "keywords": ["dust bowl", "okie", "okies", "california", "drought", "farming", "migrant", "pea-picker"]
    },
    "order_9066": {
        "title": "Archival Document: Civilian Exclusion Order (Executive Order 9066)",
        "cdn_url": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/thumb/0/02/Instructions_to_japanese.png/800px-Instructions_to_japanese.png&output=jpg",
        "caption": "Wartime Civil Control Administration notice posted in California ordering Japanese American removal. (National Archives Catalog)",
        "keywords": ["9066", "internment", "japanese", "manzanar", "exclusion", "relocation", "korematsu"]
    },
    "infamy_speech": {
        "title": "Archival Document: Annotated 'Day of Infamy' Address (Dec 8, 1941)",
        "cdn_url": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/thumb/d/df/Day-of-infamy-draft1-page1.jpg/800px-Day-of-infamy-draft1-page1.jpg&output=jpg",
        "caption": "FDR's handwritten revisions requesting Congress declare war on Japan. (FDR Presidential Library / FRANKLIN)",
        "keywords": ["pearl harbor", "infamy", "december 7", "declaration of war", "hawaii", "navy"]
    },
    "ccc_workers": {
        "title": "Photograph: Civilian Conservation Corps Planting Crew",
        "cdn_url": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/thumb/d/d3/CCC_workers_planting_seedlings.jpg/800px-CCC_workers_planting_seedlings.jpg&output=jpg",
        "caption": "Young men planting trees to halt topsoil erosion and build state and national parks. (National Archives Catalog)",
        "keywords": ["ccc", "civilian conservation", "planting", "forestry", "trees", "erosion", "work camp"]
    },
    "court_packing": {
        "title": "Political Cartoon: Judicial Reorganization Bill (1937)",
        "cdn_url": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Court_packing_cartoon_1937.jpg/800px-Court_packing_cartoon_1937.jpg&output=jpg",
        "caption": "Contemporary debate after the Supreme Court struck down early New Deal laws like Schechter Poultry. (Library of Congress)",
        "keywords": ["court-packing", "court packing", "supreme court", "nine old men", "schechter", "unconstitutional"]
    },
    "pacific_theater_map": {
        "title": "Military Map: Pacific Ocean Theater of World War II",
        "cdn_url": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Pacific_Area_-_World_War_II.jpg/800px-Pacific_Area_-_World_War_II.jpg&output=jpg",
        "caption": "Allied Command operational boundaries across the Pacific theater. (Office of the Historian, FRUS)",
        "keywords": ["pacific", "midway", "island hopping", "nimitz", "macarthur", "guadalcanal", "fleet"]
    },
    "fireside_photo": {
        "title": "Photograph: FDR Delivering a Fireside Chat",
        "cdn_url": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/thumb/0/05/FDR_fireside_chat_1933.jpg/800px-FDR_fireside_chat_1933.jpg&output=jpg",
        "caption": "President Roosevelt addressing the nation over the radio networks from the White House. (FDR Library)",
        "keywords": ["fireside", "radio", "broadcast", "bank holiday", "hundred days", "addressing the nation"]
    }
}

def identify_visual_key(tag_match: str, text_corpus: str) -> str:
    """
    Guarantees an image/map is found either via the LLM tag OR via keyword detection.
    """
    if tag_match and tag_match in VISUAL_ARCHIVE:
        return tag_match

    # Fallback: scan user query + FDR answer for historical topics
    lower_text = text_corpus.lower()
    for key, data in VISUAL_ARCHIVE.items():
        if any(kw in lower_text for kw in data["keywords"]):
            return key
    return None

# -----------------------------------------------------------------------------
# 4. FDR System Instructions
# -----------------------------------------------------------------------------
SYSTEM_INSTRUCTION = """
You are Franklin Delano Roosevelt (FDR), 32nd President of the United States.
You are conversing with a California 10th-grade high school history student.

Voice, Reading Level & Tone:
1. Speak in your warm, reassuring fireside chat cadence ("My friends...", "Let us be clear...").
2. Match a 10th-grade reading level: clear, direct, and historically accurate without overly dense Victorian phrasing.
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
- [IMAGE: court_packing]
- [IMAGE: pacific_theater_map]
- [IMAGE: fireside_photo]
"""

# -----------------------------------------------------------------------------
# 5. Session State & Memory (Strictly 6 Previous Questions)
# -----------------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []

def render_artifact_box(image_key: str):
    """Renders the primary source photograph or map with zero hotlinking errors."""
    if image_key and image_key in VISUAL_ARCHIVE:
        item = VISUAL_ARCHIVE[image_key]
        st.image(
            item["cdn_url"],
            caption=f"🏛️ {item['title']} — {item['caption']}",
            use_container_width=True
        )

# -----------------------------------------------------------------------------
# 6. Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image(
        "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/thumb/4/42/FDR_1944_Color_Portrait.jpg/480px-FDR_1944_Color_Portrait.jpg&output=jpg",
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
# 7. Main Chat UI & Historic Turn Replay
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
            render_artifact_box(turn["image_key"])

# -----------------------------------------------------------------------------
# 8. Chat Input & Processing Pipeline
# -----------------------------------------------------------------------------
user_input = st.chat_input("Ask Mr. President a question...")

if user_input:
    # Render user prompt immediately
    with st.chat_message("user"):
        st.markdown(user_input)

    # Restrict context payload: previous 5 completed turns + current input = 6 questions
    recent_turns = st.session_state.history[-5:]
    contents_payload = []
    for past in recent_turns:
        contents_payload.append(past["question"])
        contents_payload.append(past["raw_answer"])
    contents_payload.append(user_input)

    # Generate response with Gemini 3.5 Flash-Lite
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

    # Extract tag if Gemini produced it
    match = re.search(r"\[IMAGE:\s*([a-zA-Z0-9_]+)\]", raw_reply)
    tag_key = match.group(1) if match else None

    # Guarantee an image is matched even if the LLM forgot to emit the tag
    image_key = identify_visual_key(tag_key, user_input + " " + raw_reply)

    # Clean the raw tag from the response text
    clean_reply = re.sub(r"\[IMAGE:\s*[a-zA-Z0-9_]+\]", "", raw_reply).strip()

    # Render Assistant Message and Historical Media
    with st.chat_message("assistant"):
        st.markdown(clean_reply)
        if image_key:
            render_artifact_box(image_key)

    # Store turn
    st.session_state.history.append({
        "question": user_input,
        "raw_answer": raw_reply,
        "clean_answer": clean_reply,
        "image_key": image_key
    })

    # Hard truncate history to the last 6 turns
    if len(st.session_state.history) > 6:
        st.session_state.history = st.session_state.history[-6:]
