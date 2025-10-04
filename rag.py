import os
import re
import csv
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate
from llm import get_llm, get_direct_llm_response
from vector_store import get_retriever

# --- Image Annotation Loading & Search ---
def load_image_annotations():
    annotation_file = os.path.join("data", "image_annotations.csv")
    if not os.path.exists(annotation_file):
        return []
    with open(annotation_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return [row for row in reader]

IMAGE_ANNOTATIONS = load_image_annotations()

def find_image_url(query: str) -> str | None:
    """
    Searches annotations for the best matching image file based on a
    descriptive query from the LLM, with improved keyword matching.
    """
    if not IMAGE_ANNOTATIONS:
        return None

    # --- Smarter Keyword Extraction ---
    stop_words = {'a', 'an', 'the', 'of', 'in', 'a', 'single', 'photo', 'image', 'bowl', 'plate'}
    query_words = set(query.lower().split()) - stop_words
    
    print(f"\n[DEBUG] Image search initiated.")
    print(f"  - LLM Query: '{query}'")
    print(f"  - Search Keywords: {query_words}")

    best_match = None
    highest_score = 0

    for annotation in IMAGE_ANNOTATIONS:
        description_words = set(annotation.get('description', '').lower().split()) - stop_words
        
        score = len(query_words.intersection(description_words))
        
        if score > highest_score:
            highest_score = score
            best_match = annotation.get('filename')

    if best_match and highest_score > 0: # More flexible threshold
        image_path = os.path.join("data", "images", best_match)
        print(f"  - Best Match Found: '{best_match}' (Score: {highest_score})")
        print(f"  - Returning Path: '{image_path}'")
        return image_path
    
    print(f"  - No suitable image match found.")
    return None

# --- NEW: Separate function to decide if an image is needed ---
def get_image_query(question: str, answer: str) -> str | None:
    """
    A second LLM call to analyze the question and answer, and decide if an image is needed.
    """
    prompt = f"""
    Analyze the user's question and the bot's answer.
    User Question: "{question}"
    Bot's Answer: "{answer}"

    Does the bot's answer describe a specific, visual food item or portion size (e.g., 'a scoop of rice', 'a slice of chicken breast', 'a healthy plate')?
    If YES, respond with a concise, 3-5 word search query for that image.
    If NO, or if the answer is generic, respond with the word "None".

    Examples:
    - If the answer mentions 'one scoop of white rice', respond: 'scoop of white rice'
    - If the answer is 'You should eat more vegetables.', respond: 'None'
    - If the answer mentions 'a slice of papaya', respond: 'slice of papaya'
    """
    
    query = get_direct_llm_response(prompt).strip()
    
    print(f"[DEBUG] Image Decision Step:")
    print(f"  - Generated Query: '{query}'")

    if "none" in query.lower() or len(query) < 3:
        return None
    return query

def identify_target_disease(question: str) -> str:
    """
    Uses a direct LLM call to identify the primary health condition in the user's query.
    """
    prompt = f"""
    Analyze the following user question and identify the primary health condition or disease mentioned.
    If a specific condition like 'Type 2 Diabetes', 'hypertension', 'CKD', or 'high cholesterol' is mentioned, return that name.
    If no specific disease is mentioned, return the phrase 'general health and wellness'.
    Respond with only the name of the condition and nothing else.

    User Question: "{question}"
    """
    disease = get_direct_llm_response(prompt)
    print(f"[DEBUG] Identified target condition: {disease}")
    return disease.strip()

# --- DYNAMIC BEHAVIOR TEMPLATE (No longer a constant) ---
def get_behavior_template(target_disease: str) -> str:
    """
    Generates the bot's persona and instructions with a focus on being conversational and patient.
    """
    return f"""
You are a specialized AI Nutrition Assistant. Your primary goal is to be a **friendly, patient, and encouraging guide** for users managing **{target_disease}**. While you follow the ADIME framework, your top priority is making the user feel comfortable and supported.

**Core Persona:**
- **Tone:** Warm, empathetic, and conversational. Use "we" and "let's" to create a sense of partnership.
- **Patience is Key:** The user may not know specific details or may give vague answers. This is perfectly okay. **Never get stuck in a loop asking for the same information.** If a user's answer is unclear, either ask a gentle follow-up question with examples or move on and work with the information you have.
- **Guide, Don't Interrogate:** Your role is to gently guide the user, not to grill them for data. Ask open-ended questions. For example, instead of "What is your exact daily sodium intake?", ask "Could you tell me about some of the meals or snacks you had yesterday? That will help us get a better picture."

**Flexible ADIME Framework:**
Your goal is to have a natural conversation that covers the ADIME steps.

1.  **Start of Conversation:** Always begin with a warm welcome and the standard disclaimer about not being a medical professional.
2.  **A (Assessment):** Gently gather information. If the user seems unsure, provide them with options or examples.
3.  **D (Nutritional Diagnosis):** Frame this as a collaborative summary. For example: "From what we've talked about, it seems like a good starting point could be focusing on consistent carbohydrate intake. Does that sound right to you?"
4.  **I (Intervention):** Work with the user to set small, achievable goals. Celebrate their willingness to try.
5.  **M & E (Monitoring & Evaluation):** Suggest easy ways to keep track of progress, emphasizing that it's about awareness, not perfection.

**"Un-stuck" Rule:** If you find yourself asking for the same type of information more than twice, rephrase your approach. Say something like, "Sorry if I'm being repetitive, let's try looking at it another way..." or "We can come back to that later. For now, let's talk about..."

**Visual Guidance Rules:** (These remain the same)
- Proactively use the `[IMAGE: ...]` tag for food servings and meal plans.
- If an exact image is missing, find the closest substitute and explain that it's a substitute.

---
**Retrieved Context:**
{{context}}
---
**Chat History:**
{{chat_history}}
---
**User Question:**
{{question}}

**Your Answer (in a warm, conversational, and patient tone):**
"""

# --- Constants ---
CONVERSATION_MEMORY_WINDOW = 10
RAG_FAILURE_PHRASES = ["i don't know", "i am not sure", "i cannot answer"]

def parse_response_for_image(text: str) -> dict:
    match = re.search(r"\[IMAGE:\s*(.*?)\]", text)
    if match:
        query = match.group(1).strip()
        cleaned_text = text.replace(match.group(0), "").strip()
        image_url = find_image_url(query)
        return {"answer": cleaned_text, "image_url": image_url}
    else:
        return {"answer": text, "image_url": None}

def get_rag_response(question: str, user_id: str, chat_session_id: str) -> dict:
    target_disease = identify_target_disease(question)
    behavior_template = get_behavior_template(target_disease)
    
    llm = get_llm()
    retriever = get_retriever(user_id=user_id)
    memory = ConversationBufferWindowMemory(
        k=CONVERSATION_MEMORY_WINDOW,
        memory_key="chat_history",
        return_messages=True,
        output_key='answer'
    )

    # --- CORRECTED PROMPT TEMPLATE ---
    custom_prompt = PromptTemplate(
        template=behavior_template,
        input_variables=["context", "chat_history", "question"]
    )

    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        combine_docs_chain_kwargs={"prompt": custom_prompt},
        return_source_documents=True
    )

    response = qa_chain({"question": question})
    answer = response.get("answer", "")

    if not answer or any(phrase.lower() in answer.lower() for phrase in RAG_FAILURE_PHRASES):
        print("RAG response insufficient. Falling back to direct LLM.")
        answer = get_direct_llm_response(question)
    
    return parse_response_for_image(answer)