import re
import streamlit as st
from google import genai
from google.genai import types

# -----------------------------------------------------------------------------
# 1. Page Configuration & Setup
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Franklin D. Roosevelt | Fireside Chat",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. Secure API Key Retrieval
# -----------------------------------------------------------------------------
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error(
        "**API Key Missing**: Please set `GEMINI_API_KEY` in `.streamlit/secrets.toml` "
        "locally or in your Streamlit Community Cloud app settings."
    )
    st.stop()

# Initialize Google GenAI Client
client = genai.Client(api_key=api_key)

# -----------------------------------------------------------------------------
# 3. Primary Source Visual Archive (Curated Maps, Photos & Artifacts)
# -----------------------------------------------------------------------------
VISUAL_ARCHIVE = {
    "fireside_photo": {
        "title": "Photograph: First Fireside Chat (March 12, 1933)",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/FDR_fireside_chat_1933.jpg/800px-FDR_fireside_chat_1933.jpg",
        "caption": "President Roosevelt addressing the nation on the banking crisis. (FDR Presidential Library / FRANKLIN Repository)",
        "trigger": "Use when discussing the banking crisis, radio chats, the first hundred days, or speaking to the American people."
    },
    "dust_bowl_california": {
        "title": "Photograph: Dust Bowl Migrants Arriving in California (1936)",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/54/Dust_Bowl_-_California_bound_1936.jpg/800px-Dust_Bowl_-_California_bound_1936.jpg",
        "caption": "Refugees from the drought-stricken Southern Plains arriving in California along Highway 99. (Dorothea Lange / Library of Congress)",
        "trigger": "Use when discussing the Dust Bowl, Okies, California farm labor, agriculture collapse, or migrant camps."
    },
    "tva_map": {
        "title": "Historical Map: Tennessee Valley Authority Regional System",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cd/TVA_Illustration_1940.jpg/800px-TVA_Illustration_1940.jpg",
        "caption": "Map of dams and public electrical development across the Tennessee River basin. (National Archives Catalog / NARA)",
        "trigger": "Use when discussing the TVA, public power, dams, rural electrification, or regional planning."
    },
    "ccc_workers": {
        "title": "Photograph: Civilian Conservation Corps at Work",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/CCC_workers_planting_seedlings.jpg/800px-CCC_workers_planting_seedlings.jpg",
        "caption": "Young men planting trees to halt soil erosion under the Emergency Conservation Work Act. (National Archives / FRANKLIN Repository)",
        "trigger": "Use when discussing the CCC, youth jobs, forestry, parks, soil conservation, or New Deal relief."
    },
    "court_packing": {
        "title": "Political Cartoon: Judicial Reorganization Bill (1937)",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Court_packing_cartoon_1937.jpg/800px-Court_packing_cartoon_1937.jpg",
        "caption": "Editorial cartoon commenting on FDR's plan to reorganize the federal judiciary after Schechter Poultry. (Library of Congress)",
        "trigger": "Use when discussing the Supreme Court, court packing, Schechter Poultry, unconstitutional New Deal acts, or 1937."
    },
    "infamy_speech": {
        "title": "Archival Document: Annotated Pearl Harbor Address (Dec 8, 1941)",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/FDR%27s_%22Day_of_Infamy%22_address_page_1.jpg/800px-FDR%27s_%22Day_of_Infamy%22_address_page_1.jpg",
        "caption": "FDR's reading copy with handwritten revisions changing 'a date which will live in world history' to 'infamy'. (FDR Presidential Library)",
        "trigger": "Use when discussing Pearl Harbor, December 7, 1941, declarations of war, or the address to Congress."
    },
    "executive_order_9066": {
        "title": "Official Document: Executive Order 9066 (Feb 19, 1942)",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/eb/Executive_Order_9066.jpg/800px-Executive_Order_9066.jpg",
        "caption": "Presidential executive order authorizing military exclusion zones and Japanese American relocation. (National Archives Catalog)",
        "trigger": "Use when discussing Japanese American internment, Manzanar, California exclusion zones, or Korematsu v. United States."
    },
    "pacific_theater_map": {
        "title": "Military Map: Pacific Ocean Areas & Allied Operations",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Pacific_Area_-_World_War_II.jpg/800px-Pacific_Area_-_World_War_II.jpg",
        "caption": "Strategy map of Allied naval and ground commands across the Pacific Theater. (Office of the Historian, FRUS)",
        "trigger": "Use when discussing the war in the Pacific, naval battles, island hopping, Midway, or General MacArthur and Admiral Nimitz."
    }
}

# -----------------------------------------------------------------------------
# 4. FDR System Instructions
# -----------------------------------------------------------------------------
image_options_prompt = "\n".join(
    [f"- [IMAGE: {k}] -> {v['trigger']}" for k, v in VISUAL_ARCHIVE.items()]
)

SYSTEM_INSTRUCTION = f"""
You are Franklin Delano Roosevelt (FDR), 32nd President of the United States.
You are conversing with a California 10th-grade high school history student.

Voice, Reading Level & Tone:
1. Speak in your authentic fireside chat voice ("My friends...", "Let us be clear...", "As I told Congress...").
2. Match a California 10th-grade high school reading level: direct, dignified, inspiring, and plain-spoken without overly dense Victorian phrasing.
3. Length Constraint: Your entire spoken response MUST BE BETWEEN A MINIMUM OF 15 WORDS AND A MAXIMUM OF 120 WORDS. Never speak less than 15 words and never exceed 120 words.

Historical Evidence & Source Grounding:
1. Base your knowledge strictly on historical primary and secondary sources:
   - Letters written by you or to you (correspondence with Eleanor Roosevelt, Winston Churchill, everyday California citizens).
   - Official government documents, executive orders (e.g., Executive Order 8802, 9066), and legislation (NIRA, Social Security Act, TVA Act, CCC, Lend-Lease).
   - Supreme Court rulings (Schechter Poultry Corp. v. United States, Korematsu v. United States).
   - Speeches (Inaugurals, Four Freedoms, Day of Infamy, Fireside Chats).
2. Archive Citation Requirement: Every single answer MUST conclude with a specific archival source citation in parentheses at the very end of your answer, citing one of these exact repositories:
   - (FDR Presidential Library & Museum, FRANKLIN Repository)
   - (Library of Congress, FDR Resource Guide)
   - (National Archives Catalog)
   - (The American Presidency Project, UC Santa Barbara)
   - (Foreign Relations of the United States, Office of the Historian)
   - (Eleanor Roosevelt Papers Project, GWU)
   - (Internet Archive, FDR Collections)
   - (FDR Library Museum Artifact Collection)

Visual Aid Selection:
When discussing a topic with a matching artifact or map, place the exact image tag at the very end of your response (after your citation):
{image_options_prompt}
Only include an image tag when directly relevant to the student's question.
"""

# -----------------------------------------------------------------------------
# 5. Session State & Memory Initialization (Previous 6 Questions)
# -----------------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []

# -----------------------------------------------------------------------------
# 6. Sidebar (Classroom Metadata & Controls)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/FDR_1944_Color_Portrait.jpg/480px-FDR_1944_Color_Portrait.jpg",
        caption="Franklin D. Roosevelt (1882–1945)",
        use_container_width=True
    )
    st.title("FDR Fireside Desk")
    st.markdown("""
    **Curriculum**: California 10th Grade U.S. & World History  
    **Model**: `gemini-3.5-flash-lite`  
    **Temperature**: `0.3`  
    **Response Limit**: 15–120 words  
    **Memory Scope**: Previous 6 questions  
    """)
    st.divider()
    st.markdown("**Designated Archival Repositories:**")
    st.caption("""
    • FRANKLIN Repository (FDR Library)  
    • Library of Congress (LOC)  
    • National Archives & Records Admin (NARA)  
    • The American Presidency Project (UCSB)  
    • Office of the Historian (FRUS)  
    • Eleanor Roosevelt Papers Project (GWU)  
    • Internet Archive (FedFlix)  
    """)
    st.divider()
    if st.button("Clear Wire / Start Over", use_container_width=True):
        st.session_state.history = []
        st.rerun()

# -----------------------------------------------------------------------------
# 7. Main Chat UI & Historic Turns
# -----------------------------------------------------------------------------
st.title("🎙️ A Fireside Chat with FDR")
st.markdown(
    "*Welcome to the Executive Office. Ask President Roosevelt about the Great Depression, "
    "the New Deal, California during the 1930s-1940s, or World War II.*"
)

# Render prior conversation turns
for turn in st.session_state.history:
    with st.chat_message("user"):
        st.markdown(turn["question"])
    with st.chat_message("assistant"):
        st.markdown(turn["clean_answer"])
        if turn.get("image_key") and turn["image_key"] in VISUAL_ARCHIVE:
            media = VISUAL_ARCHIVE[turn["image_key"]]
            st.image(
                media["url"],
                caption=f"{media['title']} — {media['caption']}",
                use_container_width=True
            )

# -----------------------------------------------------------------------------
# 8. User Interaction & Gemini Query Pipeline
# -----------------------------------------------------------------------------
user_input = st.chat_input("Ask Mr. President a question...")

if user_input:
    # Display the user's question immediately
    with st.chat_message("user"):
        st.markdown(user_input)

    # Restrict memory payload: Last 5 turns + current question = exactly 6 questions in context
    recent_turns = st.session_state.history[-5:]
    contents_payload = []
    for past in recent_turns:
        contents_payload.append(past["question"])
        contents_payload.append(past["raw_answer"])
    contents_payload.append(user_input)

    # Call Gemini 3.5 Flash-Lite at 0.3 Temperature
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
        raw_reply = (
            f"My friends, the telegraph wires have suffered an unexpected disruption: {str(e)}. "
            "(National Archives Catalog)"
        )

    # Parse and extract image tags: [IMAGE: key_name]
    image_match = re.search(r"\[IMAGE:\s*([a-zA-Z0-9_]+)\]", raw_reply)
    image_key = image_match.group(1) if image_match else None

    # Clean the response text so raw tags are not displayed to students
    clean_reply = re.sub(r"\[IMAGE:\s*[a-zA-Z0-9_]+\]", "", raw_reply).strip()

    # Render FDR's response & historical media
    with st.chat_message("assistant"):
        st.markdown(clean_reply)
        if image_key and image_key in VISUAL_ARCHIVE:
            media = VISUAL_ARCHIVE[image_key]
            st.image(
                media["url"],
                caption=f"{media['title']} — {media['caption']}",
                use_container_width=True
            )

    # Save turn to session state
    st.session_state.history.append({
        "question": user_input,
        "raw_answer": raw_reply,
        "clean_answer": clean_reply,
        "image_key": image_key
    })

    # Strict truncation: ensure only the previous 6 questions are kept in memory
    if len(st.session_state.history) > 6:
        st.session_state.history = st.session_state.history[-6:]
