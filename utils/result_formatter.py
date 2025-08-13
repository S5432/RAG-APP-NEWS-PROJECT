from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import logging
import sys
import os
import warnings  
from llm.setup_llm import llm


warnings.filterwarnings("ignore")  

# ----------------- Logging Setup -----------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


#----------------- Create a file handler and set the formatter-----------------
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s')


#----------------- Create a stream handler and set the formatter-----------------
stream_handler = logging.StreamHandler(sys.stdout)  # Output to console
stream_handler.setFormatter(formatter)

#----------------- Add the handlers to the logger-----------------
logger.addHandler(stream_handler)



# ----------------- Prompt and Chain Setup -----------------
formatter_prompt = PromptTemplate.from_template("""
You are a smart assistant that only returns information directly relevant to the user's question, based on the data below.

If the question asks for a URL, return ONLY the URL without additional explanation.
If the question asks for something else, summarize clearly using only the relevant parts of the raw data.

Instructions:
                                                
- Respect the user's intent in the question.
- Use the `Result` section to form your answer. Do not go beyond this data.
- Format your response exactly how the user asks (e.g., summary, detailed info, bullet list, structured text, etc.).
- If the user asks for:
  - "List articles" → List the article titles, if user ask so then provide article title with authors and publication dates if available.
  - "Summary of article(s)" → Briefly summarize article  or content of each article and provide answer in 3-4 sentence paragraph and bullet points if required.
  - "Detailed info" → Show full details of each article (full description and answer full article description).
  - "Detailed info", "More info", "Full description", "Tell me more", "In-depth article" → 
    Expand the content into a full, richly detailed explanation of at least 500 to 1000 words. 
    Discuss the main topic, background, key takeaways, author perspectives, and implications. 
    Write in clear paragraphs, headings and use bullet points and include structure if needed.
  - "Schema-related info" → Extract and explain schema details present in the result.
- Keep your tone clear, informative, and aligned with user preferences.

Avoid adding extra information not requested.

Important Rule:
- You MUST NOT use any external world knowledge.
- Only answer based on the given database or embedding data.
- If the query is outside this scope, reply: "I only assist with music-related questions."
- ALWAYS include the source URL when it's available in the raw data, regardless of the query type.
- When mentioning an article, always provide the URL if it exists in the raw data.

---
Question: {question}
Source: {source}
Raw Data:
{raw_result}

Now format a helpful answer. Write clearly. Use bullets if needed.

Answer:
""")


#------------------ Check if llm is initialized ---------------------
if llm:
    formatter_chain = LLMChain(llm=llm, prompt=formatter_prompt)
    logger.info("Formatter chain initialized successfully.")
else:
    formatter_chain = None # Or handle the lack of LLM as appropriate for your application
    logger.warning("LLM not initialized, formatter chain will not be functional.")



# ----------------- Function Definition -----------------
def format_result(question: str, raw_result: str, source: str) -> str:
    """Formats the raw result using the LLM chain.

    Args:
        question: The user's question.
        raw_result: The raw result to format.
        source: The source of the data.

    Returns:
        The formatted result as a string, or an error message if formatting fails.
    """
    if not formatter_chain: # Check if the chain exists before attempting to use it
        logger.error("Cannot format result because the formatter chain is not initialized.")
        return f"Apologies, I cannot format the result as the LLM is not set up. Raw result:\n{raw_result.strip()}"

    try:
        response = formatter_chain.invoke({
            "question": question.strip(),
            "raw_result": raw_result.strip(),
            "source": source.strip()
        })
        formatted_text = response.get("text", "").strip()  # Use .get() to handle potential missing 'text' key
        logger.info(f"[Formatter] Successfully formatted result for source: {source}")
        return formatted_text
    except Exception as e:
        logger.error(f"[Formatter Error] Error during formatting: {e}")
        return f"{raw_result.strip()}  \n\n(Note: Please try rephrasing or asking a different question.)"