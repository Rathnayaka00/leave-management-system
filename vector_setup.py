import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

# Load environment variables
load_dotenv()

# Get OpenAI API Key
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment or .env file.")

# Set OpenAI API key
os.environ["OPENAI_API_KEY"] = openai_api_key

# Load the PDF file
loader = PyPDFLoader("D:/Projects/RAG Assignment/resources/leave.pdf")  # Ensure the file path is correct
docs = loader.load()

# Split the document into chunks
text_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
splits = text_splitter.split_documents(docs)

# Create embeddings and vectorstore
embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = Chroma.from_documents(documents=splits, embedding=embedding_model)

# Define the persistence location (the folder where the vectorstore will be saved)
persist_directory = "vectorstore_data"

# Persist the vectorstore to the specified directory
vectorstore.persist()  # Save without the 'directory' argument
vectorstore = Chroma(persist_directory=persist_directory)  # Initialize again with the directory

print("Vectorstore created and saved successfully!")
