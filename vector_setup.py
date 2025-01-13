import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment or .env file.")

os.environ["OPENAI_API_KEY"] = openai_api_key

def vectorize_pdf(file_path: str):

    try:
        loader = PyPDFLoader(file_path)  
        docs = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
        splits = text_splitter.split_documents(docs)

        embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
        vectorstore = Chroma.from_documents(documents=splits, embedding=embedding_model)

        persist_directory = "vectorstore_data"
        vectorstore.persist()  
        vectorstore = Chroma(persist_directory=persist_directory)

        return "Vectorstore created and saved successfully!"
    except Exception as e:
        raise Exception(f"Error during vectorization: {str(e)}")
