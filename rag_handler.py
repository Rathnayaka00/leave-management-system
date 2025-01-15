import os
import json
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment or .env file.")

os.environ["OPENAI_API_KEY"] = openai_api_key

persist_directory = "vectorstore_data"
embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")

vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embedding_model)

retriever = vectorstore.as_retriever()

system_prompt = (
    "You are the head of the HR department. You are responsible for approving or rejecting leave requests based on company policies. "
    "Use the following context to determine whether the leave request can be accepted or rejected. "
    "If the leave request is valid according to the company policies, output '1' (accepted). "
    "If the leave request is not valid according to the company policies, output '0' (rejected). "
    "Explain the reason clearly. Your output must strictly follow this format:\n\n"
    "Binary Result: <0 or 1>\n"
    "Explanation: <Detailed Explanation>"
    "\n\n"
    "{context}"
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)

llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
qa_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, qa_chain)

def handle_request(leave_request: str):
    response = rag_chain.invoke({"input": leave_request})

    binary_result = None
    explanation = None
    if response and "answer" in response:
        answer = response["answer"]
        if "Binary Result:" in answer and "Explanation:" in answer:
            try:
                binary_result = answer.split("Binary Result:")[1].split("\n")[0].strip()
                explanation = answer.split("Explanation:")[1].strip()
            except IndexError:
                explanation = "Unable to parse explanation from the output."
        else:
            explanation = "Output format does not match the expected format."

    output = {
        "output": binary_result,
        "explanation": explanation
    }
    return json.dumps(output, indent=4)

if __name__ == "__main__":
    user_input = input("Enter your leave request: ")
    result = handle_request(user_input)
    print(result)
