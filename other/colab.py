import os
from google.colab import userdata

from langchain_openai import ChatOpenAI
os.environ["OPENAI_API_KEY"] = userdata.get('OPENAI_API_KEY')
llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

from langchain_openai import OpenAIEmbeddings
embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")

from langchain_community.document_loaders import PyPDFLoader
loader = PyPDFLoader("/content/leave.pdf")
docs = loader.load()

from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
splits = text_splitter.split_documents(docs)

from langchain_chroma import Chroma

vectorstore = Chroma.from_documents(documents=splits, embedding=embedding_model)

retriever = vectorstore.as_retriever()

from langchain_core.prompts import ChatPromptTemplate

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

from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

# Create QA chain
qa_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, qa_chain)

# Invoke the chain
response = rag_chain.invoke({"input": "I face an unexpected injury."})

# Extract and display the answer
print(response["answer"])