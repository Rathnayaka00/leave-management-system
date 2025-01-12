import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

# Load environment variables from .env file
load_dotenv()

# Get the OpenAI API key from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment or .env file.")

# Set OpenAI API key
os.environ["OPENAI_API_KEY"] = openai_api_key

# Load the leave policy document
loader = PyPDFLoader("leave.pdf")  # Ensure the file path is correct
docs = loader.load()

# Split the document into smaller chunks for processing
text_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
splits = text_splitter.split_documents(docs)

# Create a vectorstore using embeddings
embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = Chroma.from_documents(documents=splits, embedding=embedding_model)

# Create a retriever from the vectorstore
retriever = vectorstore.as_retriever()

# Define the system prompt
system_prompt = (
    "You are the head of the HR department. You are responsible for approving or rejecting leave requests based on company policies. "
    "Use the following context to determine whether the leave request can be accepted or rejected. "
    "If the leave request is valid according to the company policies, output '1' (accepted). "
    "If the leave request cannot be accepted according to the company policies, output '0' (rejected). "
    "Explain the reason clearly. Your output must strictly follow this format:\n\n"
    "Binary Result: <0 or 1>\n"
    "Explanation: <Detailed Explanation>"
    "\n\n"
    "{context}"
)

# Create the prompt template
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)

# Initialize the LLM and QA chain
llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
qa_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, qa_chain)

# Input for leave request
leave_request = "I face an unexpected injury."

# Invoke the RAG chain
response = rag_chain.invoke({"input": leave_request})

# Format the output as JSON
binary_result = None
explanation = None

# Parse the response to extract binary result and explanation
if response and "answer" in response:
    answer = response["answer"]
    # Parse binary result and explanation
    if "Binary Result:" in answer and "Explanation:" in answer:
        try:
            binary_result = answer.split("Binary Result:")[1].split("\n")[0].strip()
            explanation = answer.split("Explanation:")[1].strip()
        except IndexError:
            explanation = "Unable to parse explanation from the output."
    else:
        explanation = "Output format does not match the expected format."

# Create the JSON output
output = {
    "binary_result": binary_result,
    "explanation": explanation
}

# Print JSON output
print(json.dumps(output, indent=4))
