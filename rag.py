import os
import re # <-- New Import
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate
from llm import get_llm, get_direct_llm_response
from vector_store import get_retriever

# --- Disease Configuration ---
# Set the target disease for the chatbot here.
TARGET_DISEASE = "Type 2 Diabetes"

# --- Image Library Configuration --- 
IMAGE_BASE_URL = "/data/images/"

def find_image_url(query: str) -> str | None:
    """
    Finds an image URL based on a descriptive query.
    This is a simple placeholder. You would build your real logic here.
    """
    # Simple keyword matching against a hypothetical library
    query = query.lower().replace(" ", "_")
    # Example: "a serving of rice" becomes "a_serving_of_rice"
    # A real implementation would use a more robust search
    image_map = {
        "serving_of_rice": "serving_of_rice.jpg",
        "serving_of_chicken": "serving_of_chicken.jpg",
    }
    for key, filename in image_map.items():
        if key in query:
            # In a real web app, this URL would point to a publicly accessible path
            # For local Streamlit, you might need to handle file paths differently
            return f"data/images/{filename}" 
    return None

# --- Hard-coded Behavior Template ---
BEHAVIOR_TEMPLATE = f"""
You are a specialized AI Nutrition Assistant. Your role is to guide and support patients in managing their specific health condition, which is **{TARGET_DISEASE}**, through the structured ADIME (Assessment, Diagnosis, Intervention, Monitoring & Evaluation) nutrition care process.

**Core Persona:**
- **Tone:** Empathetic, professional, clear, and encouraging.
- **Limitation:** You are an AI educational tool, not a replacement for a human healthcare provider. Always clarify this. Your guidance is based on established nutritional guidelines, but all plans should be reviewed with a qualified dietitian or doctor.

**Primary Directive: The ADIME Framework**
Your primary goal is to walk the patient through the ADIME framework one step at a time. Do not overwhelm the user.

**Interaction Flow:**

1.  **Start of Conversation:**
    - Always begin the first interaction with the disclaimer: "I am an AI assistant designed for educational purposes. I am not a substitute for a doctor or registered dietitian. Please consult with a healthcare professional before making any changes to your health regimen."
    - Initiate the 'Assessment' step.

2.  **A: Assessment:**
    - **Goal:** Gather information on dietary intake, physical signs (weight, energy), lifestyle, and their understanding of nutrition for {TARGET_DISEASE}.
    - **Instruction:** Do not proceed until you have gathered sufficient information.

3.  **D: Nutritional Diagnosis:**
    - **Goal:** Identify and label a *nutritional* problem (e.g., "inconsistent carbohydrate intake," "excessive sodium intake"). This is not a medical diagnosis.
    - **Instruction:** Propose a nutritional diagnosis to the user and ask for their confirmation before proceeding.

4.  **I: Intervention:**
    - **Goal:** Provide specific, actionable advice and education to address the nutritional diagnosis.
    - **Instruction:** Collaborate with the user to set realistic and small goals (e.g., "swap one sugary drink for water each day").

5.  **M & E: Monitoring and Evaluation:**
    - **Goal:** Establish a plan for the patient to track their progress.
    - **Instruction:** Suggest simple tracking methods (e.g., "keep a brief food diary") and propose a follow-up to discuss their progress.

**Safety Rules:**
- **Emergency Trigger:** If the user mentions "chest pain," "dizziness," "severe pain," "allergic reaction," or any other medical emergency, you must immediately stop and respond: "These symptoms could be serious. Please contact your doctor or emergency services immediately."
- **No Medical Advice:** Do not prescribe supplements, medications, or specific medical treatments.
- **Privacy:** Remind users not to share sensitive personal information (full name, address, etc.).
- **Stay Focused:** Gently guide the conversation back to the ADIME process if the user goes off-topic.

---
Now, begin the conversation with the user based on the context below.

**Chat History:**
{{chat_history}}

**User Question:**
{{question}}

**Your Answer:**
"""

# --- Constants ---
CONVERSATION_MEMORY_WINDOW = 10
RAG_FAILURE_PHRASES = [
    "I don't know", "I am not sure", "I cannot answer",
    "Sorry, I encountered an issue"
]

def find_image_url(query: str) -> str | None:
    """
    Searches the data/images directory for the best matching image file
    based on a descriptive query.
    """
    image_dir = os.path.join("data", "images")
    if not os.path.exists(image_dir):
        return None

    # Simplify the query into keywords
    query_words = set(query.lower().replace("serving of ", "").replace("of", "").replace("a", "").split())

    best_match = None
    highest_score = 0

    # Search through all files in the image directory
    for filename in os.listdir(image_dir):
        # Simplify the filename into keywords for matching
        file_words = set(filename.lower().replace(".png", "").replace(".jpg", "").replace("_", " ").split())
        
        # Score the match based on the number of overlapping keywords
        score = len(query_words.intersection(file_words))
        
        if score > highest_score:
            highest_score = score
            best_match = os.path.join(image_dir, filename)

    if highest_score > 1: # Require at least a few keywords to match
        print(f"Image match found for query '{query}': {best_match}")
        return best_match
    
    print(f"No suitable image match found for query: '{query}'")
    return None


def parse_response_for_image(text: str) -> dict:
    """
    Parses the LLM's text output to find an image request tag.
    """
    match = re.search(r"\[IMAGE:\s*(.*?)\]", text)
    if match:
        query = match.group(1).strip()
        # Remove the tag from the text that will be displayed
        cleaned_text = text.replace(match.group(0), "").strip()
        image_url = find_image_url(query)
        return {"answer": cleaned_text, "image_url": image_url}
    else:
        return {"answer": text, "image_url": None}

def get_rag_response(question: str, user_id: str, chat_session_id: str) -> str:
    """
    Generates a response using the RAG chain with a hard-coded behavior prompt.
    """
    llm = get_llm()
    retriever = get_retriever(user_id=user_id)

    memory = ConversationBufferWindowMemory(
        k=CONVERSATION_MEMORY_WINDOW,
        memory_key="chat_history",
        return_messages=True,
        output_key='answer'
    )

    # --- Create a Prompt Template with the Behavior ---
    custom_prompt = PromptTemplate(
        template=BEHAVIOR_TEMPLATE,
        input_variables=["chat_history", "question"]
    )

    # --- Conversational RAG Chain with Custom Prompt ---
    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        combine_docs_chain_kwargs={"prompt": custom_prompt},
        return_source_documents=True
    )

    response = qa_chain({"question": question})
    answer = response.get("answer", "")

    # --- Fallback to direct LLM if RAG fails ---
    if not answer or any(phrase.lower() in answer.lower() for phrase in RAG_FAILURE_PHRASES):
        print("RAG response insufficient. Falling back to direct LLM.")
        # The direct response will still benefit from the overall model fine-tuning,
        # but won't be explicitly constrained by the ADIME prompt in the same way.
        answer = get_direct_llm_response(question)

    return answer