import streamlit as st
from google import genai
from google.genai import types

# Page setup
st.set_page_config(
    page_title="Fireside Chat with FDR",
    page_icon="🎙️",
    layout="centered"
)

# ---------------------------------------------------------
# 1. API Key Retrieval (Hidden in Streamlit Secrets)
# ---------------------------------------------------------
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Missing Gemini API Key. Please add `GEMINI_API_KEY` to `.streamlit/secrets.toml`.")
    st.stop()

# Initialize Google GenAI client
client = genai.Client(api_key=api_key)

# ---------------------------------------------------------
# 2. FDR System Instruction & Archival Grounding
# ---------------------------------------------------------
FDR_SYSTEM_PROMPT = """
You are Franklin Delano Roosevelt (FDR), the 32nd President of the United States. 
You are speaking directly to 10th-grade American high school students (ages 15-16).

VOICE & READING LEVEL:
- Adopt FDR's warm, resolute, and reassuring voice (reminiscent of your 'Fireside Chats').
- Speak in the first person ("I", "my administration", "my friends").
- Use language and vocabulary tailored to a 10th-grade reading level. Keep concepts accessible, clear, and engaging without being patronizing.
- Clearly explain 1930s and 1940s economic, governmental, and military terms when they arise.

PRIMARY & SECONDARY HISTORICAL KNOWLEDGE BASE:
Base your answers on:
1. FDR Presidential Library Digitized Collections (Fireside Chats, White House files, personal diaries, press conferences).
2. National Archives Catalog (Executive Orders such as EO 8802 and EO 9066, New Deal agency records).
3. The American Presidency Project (Inaugural addresses, State of the Union messages, radio addresses).
4. Eleanor Roosevelt Papers Project (Personal and political letters between Franklin and Eleanor, public correspondence).
5. All correspondence: Private and public letters to and from American citizens, allied leaders (e.g., Winston Churchill), cabinet members, and lawmakers.
6. Major Court Battles & Legislation: The New Deal laws (CCC, WPA, Social Security Act of 1935, FLSA, TVA), the 1937 Judicial Procedures Reform Bill ("court-packing"), and Supreme Court cases (Schechter Poultry v. US, US v. Butler, West Coast Hotel v. Parrish, Korematsu v. US).

STRICT OUTPUT CONSTRAINTS:
1. WORD COUNT: Your entire response MUST be between 15 words minimum and 120 words maximum.
2. CITATION/SOURCE: At the very end of every reply, include a specific source tag showing where your answer originates, formatted exactly as:
   [Source: <Archive Name> – <Document/Speech/Letter Title, Year>]
   Valid archives to reference include:
   - FDR Presidential Library Digitized Collections
   - National Archives Catalog
   - The American Presidency Project
   - Eleanor Roosevelt Papers Project
"""

# ---------------------------------------------------------
# 3. Session State & History Management (Last 6 Questions)
# ---------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

def get_trimmed_history(messages, max_questions=6):
    """
    Limits conversational context sent to Gemini to only the 
    last `max_questions` user queries and their respective answers.
    """
    user_indices = [i for i, m in enumerate(messages) if m["role"] == "user"]
    if len(user_indices) > max_questions:
        cutoff = user_indices[-max_questions]
        return messages[cutoff:]
    return messages

# UI Header
st.title("🎙️ Fireside Chat with Franklin D. Roosevelt")
st.caption("Ask President Roosevelt about the Great Depression, the New Deal, WWII, and his presidency.")

# Display historical messages in the chat UI
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ---------------------------------------------------------
# 4. User Interaction & Generation
# ---------------------------------------------------------
if prompt := st.chat_input("Ask President Roosevelt a question..."):
    # Append user question
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare only the last 6 questions + answers for context
    active_history = get_trimmed_history(st.session_state.messages, max_questions=6)

    # Format history into Gemini content turns
    contents = []
    for m in active_history:
        contents.append(
            types.Content(
                role="user" if m["role"] == "user" else "model",
                parts=[types.Part.from_text(text=m["content"])]
            )
        )

    # Generate model response using gemini-3.5-flash-lite at temperature 0.3
    with st.chat_message("assistant"):
        with st.spinner("President Roosevelt is drafting a reply..."):
            try:
                response = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=FDR_SYSTEM_PROMPT,
                        temperature=0.3,
                        max_output_tokens=300,
                    )
                )
                fdr_reply = response.text.strip()
                st.markdown(fdr_reply)
                st.session_state.messages.append({"role": "assistant", "content": fdr_reply})

            except Exception as e:
                st.error(f"Error communicating with Gemini: {e}")
