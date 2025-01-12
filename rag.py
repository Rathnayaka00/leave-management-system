import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

# Load environment variables from .env file
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment or .env file.")

os.environ["OPENAI_API_KEY"] = openai_api_key


def initialize_rag_pipeline(pdf_path):
    """
    Initializes the RAG pipeline by loading the PDF, splitting documents, and setting up the retriever and chain.
    """
    # Load the leave policy document
    loader = PyPDFLoader(pdf_path)
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

    return rag_chain


def handle_request(rag_chain, leave_request):
    """
    Handles a leave request using the RAG pipeline and returns the result as a JSON object.
    """
    response = rag_chain.invoke({"input": leave_request})

    # Extract binary result and explanation
    binary_result = None
    explanation = None

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

    return {
        "binary_result": binary_result,
        "explanation": explanation,
    }


if __name__ == "__main__":
    # Only executes if the script is run directly
    pdf_path = "resources/leave.pdf"  # Update the path as needed
    leave_request = "I face an accident."

    # Initialize the pipeline
    rag_chain = initialize_rag_pipeline(pdf_path)

    # Process the leave request
    result = handle_request(rag_chain, leave_request)

    # Print the result as JSON
    print(json.dumps(result, indent=4))
