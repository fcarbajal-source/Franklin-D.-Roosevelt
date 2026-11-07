import streamlit as st
from google import genai
from google.genai import types

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="FDR Fireside Chatbot",
    page_icon="🎙️",
    layout="centered"
)

# ---------------------------------------------------------
# API Key Management
# ---------------------------------------------------------
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Missing Gemini API Key. Please configure `.streamlit/secrets.toml` or Streamlit Cloud Secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

# ---------------------------------------------------------
# Curated Primary Source Visuals (Maps & Artifacts)
# ---------------------------------------------------------
MEDIA_VAULT = {
    "tva": {
        "title": "Map: Tennessee Valley Authority Project (1930s)",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cd/TVA_Illustration_1940.jpg/800px-TVA_Illustration_1940.jpg",
        "caption": "Map and scope of the TVA regional development system (Library of Congress / NARA).",
        "keywords": ["tva", "tennessee valley", "dam", "electricity", "rural electrification"]
    },
    "dust_bowl": {
        "title": "Map: Dust Bowl Migration to California",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/54/Dust_Bowl_-_California_bound_1936.jpg/800px-Dust_Bowl_-_California_bound_1936.jpg",
        "caption": "Migrant family arriving in California from the Oklahoma Dust Bowl, 1936 (Dorothea Lange, LOC / Farm Security Administration).",
        "keywords": ["dust bowl", "california", "migration", "okie", "drought", "farming", "agriculture"]
    },
    "fireside": {
        "title": "Photo: FDR Delivering a Fireside Chat",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/FDR_fireside_chat_1933.jpg/800px-FDR_fireside_chat_1933.jpg",
        "caption": "President Roosevelt broadcasting a Fireside Chat to the American public, 1933 (FDR Presidential Library / FRANKLIN Repository).",
        "keywords": ["fireside chat", "radio", "speech", "banking", "morale", "first 100 days"]
    },
    "court_packing": {
        "title": "Artifact: Judicial Reorganization Bill Political Cartoon (1937)",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Court_packing_cartoon_1937.jpg/800px-Court_packing_cartoon_1937.jpg",
        "caption": "Contemporary illustration of FDR's 1937 Judicial Procedures Reform Bill debate (Library of Congress).",
        "keywords": ["supreme court", "court packing", "judicial", "unconstitutional", "schechter"]
    },
    "pearl_harbor": {
        "title": "Document: Draft of the 'Day of Infamy' Address (Dec 8, 1941)",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/FDR%27s_%22Day_of_Infamy%22_address_page_1.jpg/800px-FDR%27s_%22Day_of_Infamy%22_address_page_1.jpg",
        "caption": "FDR's annotated typed reading copy for Congress declaring war on Japan (National Archives Catalog / FDR Library).",
        "keywords": ["pearl harbor", "infamy", "japan", "war", "december 7", "congress"]
    },
    "internment": {
        "title": "Document & Map: Executive Order 9066 & Exclusion Zones",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/eb/Executive_Order_9066.jpg/800px-Executive_Order_9066.jpg",
        "caption": "Executive Order 9066 authorizing military exclusion areas in California and the West (National Archives).",
        "keywords": ["9066", "internment", "japanese", "manzanar", "california", "korematsu", "exclusion"]
    },
    "ww2_pacific": {
        "title": "Map: Pacific Ocean Theater of World War II",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Pacific_Area_-_World_War_II.jpg/800px-Pacific_Area_-_World_War_II.jpg",
        "caption": "Allied Command map of operations in the Pacific (FRUS / US Army Center of Military History).",
        "keywords": ["pacific", "midway", "navy", "japan", "island hopping"]
    }
}

def detect_relevant_media(query_text: str):
    """Finds historical photographs or maps matching user inquiry."""
    q = query_text.lower()
    matches = []
    for media_id, item in MEDIA_VAULT.items():
        if any(kw in q for kw in item["keywords"]):
            matches.append(item)
    return matches

# ---------------------------------------------------------
# FDR System Prompt
# ---------------------------------------------------------
SYSTEM_INSTRUCTION = """
You are Franklin Delano Roosevelt (FDR), 32nd President of the United States.
You are conversing with a 10th-grade California high school student studying U.S. and Modern World History.

Persona & Voice Guidelines:
1. Speak in your authentic, reassuring "fireside chat" cadence ("My friends...", "Let us be clear..."). 
2. Match a 10th-grade high school reading level: clear, direct, articulate, and historically accurate without overly archaic vocabulary.
3. Length Constraint: Every answer MUST be strictly between 15 and 120 words. Never go below 15 words and never exceed 120 words.
4. Historical Grounding: Root every explanation in primary and secondary evidence:
   - Letters written by or to you (Eleanor Roosevelt, Winston Churchill, everyday citizens).
   - Congressional acts and legislation (CCC, WPA, Social Security Act, TVA, Lend-Lease Act, NIRA).
   - Presidential speeches (Inaugural Addresses, Four Freedoms, Pearl Harbor Address, Fireside Chats).
   - Official government records, Supreme Court rulings (Schechter Poultry v. U.S., Korematsu v. U.S.).
5. Citation Requirement: Conclude every single answer with an explicit primary archive citation in parentheses referencing one of these repositories:
   - FDR Presidential Library & Museum (FRANKLIN Repository)
   - Library of Congress (FDR Resource Guide)
   - National Archives Catalog (NARA)
   - The American Presidency Project (UC Santa Barbara)
   - Foreign Relations of the United States (FRUS), Office of the Historian
   - Eleanor Roosevelt Papers Project (George Washington University)
   - FDR Library Museum Artifact Collection
"""

# ---------------------------------------------------------
# Memory Management (Strictly Last 6 Questions)
# ---------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []

# Sidebar
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/FDR_1944_Color_Portrait.jpg/480px-FDR_1944_Color_Portrait.jpg", caption="Franklin D. Roosevelt (1882–1945)")
    st.subheader("Fireside Classroom")
    st.markdown("""
    **Audience**: 10th Grade U.S. History  
    **Model**: `gemini-3.5-flash-lite`  
    **Temperature**: `0.3`  
    **Memory**: Last 6 questions retained  
    **Output Limit**: 15–120 words  
    """)
    if st.button("Reset Conversation"):
        st.session_state.history = []
        st.rerun()

st.title("🎙️ A Fireside Chat with FDR")
st.caption("Ask President Roosevelt about the Great Depression, the New Deal, California in the 1930s-40s, and World War II.")

# Display Chat History
for turn in st.session_state.history:
    with st.chat_message("user"):
        st.markdown(turn["question"])
    with st.chat_message("assistant"):
        st.markdown(turn["answer"])
        if turn.get("media"):
            for m in turn["media"]:
                st.image(m["url"], caption=f"{m['title']} — {m['caption']}", use_container_width=True)

# ---------------------------------------------------------
# User Interaction & Gemini Query
# ---------------------------------------------------------
user_input = st.chat_input("Ask a question, my friend...")

if user_input:
    # Append the new user turn to history
    with st.chat_message("user"):
        st.markdown(user_input)

    # Maintain window: Keep only previous 6 questions (the current + up to 5 preceding)
    recent_turns = st.session_state.history[-5:]

    # Construct conversation history payload for the model
    contents = []
    for past in recent_turns:
        contents.append(past["question"])
        contents.append(past["answer"])
    contents.append(user_input)

    # Detect contextual maps/images
    detected_media = detect_relevant_media(user_input)

    # Generate response using Gemini 3.5 Flash-Lite
    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.3,
            )
        )
        fdr_reply = response.text.strip()

    except Exception as e:
        fdr_reply = f"My friends, we face technical difficulties with the radio wire: {str(e)}"

    # Render FDR response
    with st.chat_message("assistant"):
        st.markdown(fdr_reply)
        for media_item in detected_media:
            st.image(media_item["url"], caption=f"{media_item['title']} — {media_item['caption']}", use_container_width=True)

    # Record turn
    st.session_state.history.append({
        "question": user_input,
        "answer": fdr_reply,
        "media": detected_media
    })

    # Enforce hard history limit: keep only the last 6 entries
    if len(st.session_state.history) > 6:
        st.session_state.history = st.session_state.history[-6:]
