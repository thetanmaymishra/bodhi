# -*- coding: utf-8 -*-
"""finalpdfcassandra.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1rUMP9Msr1x8VAqsmuwPIaGGuBymAyJ6e
"""

from PyPDF2 import PdfReader
from langchain.vectorstores.cassandra import Cassandra
from langchain.indexes.vectorstore import VectorStoreIndexWrapper
from langchain.llms import OpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from flask import Flask, render_template, request, jsonify
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from typing_extensions import Concatenate
import cassio
from datasets import load_dataset

ASTRA_DB_APPLICATION_TOKEN = "AstraCS:RYSEsgeCsJnSdLwHLUehxGOB:6e06dfaea59380f6e0d422e74244110151e7ac0e8854d916ffa7eb0f4adc7f92"  # enter the "AstraCS:..." string found in in your Token JSON file
ASTRA_DB_ID = "d79f649d-bc75-4e8b-bc65-f34a431770fc"  # enter your Database ID
OPENAI_API_KEY = "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"  # enter your OpenAI key

# Initialize CassIO
cassio.init(token=ASTRA_DB_APPLICATION_TOKEN, database_id=ASTRA_DB_ID)

# Initialize OpenAI components
llm = OpenAI(openai_api_key=OPENAI_API_KEY)
embedding = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

# Initialize Astra Cassandra Vector Store
astra_vector_store = Cassandra(
    embedding=embedding,
    table_name="qa_mini_demo",
    session=None,
    keyspace=None,
)

# Load PDF and extract text
pdfreader = PdfReader("C:/Users/VASU/OneDrive/Desktop/MedicalChatbot-Using-Llama2/data/book.pdf")
raw_text = ''
for i, page in enumerate(pdfreader.pages):
    content = page.extract_text()
    if content:
        raw_text += content

# Split the text using Character Text Split
text_splitter = CharacterTextSplitter(
    separator="\n",
    chunk_size=800,
    chunk_overlap=200,
    length_function=len,
)
texts = text_splitter.split_text(raw_text)

# Add texts to Astra Cassandra Vector Store
astra_vector_store.add_texts(texts[:50])

# Initialize Vector Store Index
astra_vector_index = VectorStoreIndexWrapper(vectorstore=astra_vector_store)

# Initialize Flask application
app = Flask(__name__)
port = 5000

# Initialize chatbot components
tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-medium")
model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-medium")
chat_history_ids = None

# Define routes
@app.route("/")
def index():
    return render_template('chat.html')

@app.route("/get", methods=["GET", "POST"])
def chat():
    msg = request.form["msg"]
    input = msg
    return get_Chat_response(input)

# Function to get chatbot response
def get_Chat_response(text):
    global chat_history_ids
    for step in range(5):
        new_user_input_ids = tokenizer.encode(str(text) + tokenizer.eos_token, return_tensors='pt')
        bot_input_ids = torch.cat([chat_history_ids, new_user_input_ids], dim=-1) if step > 0 else new_user_input_ids 
        chat_history_ids = model.generate(bot_input_ids, max_length=1000, pad_token_id=tokenizer.eos_token_id)
        return tokenizer.decode(chat_history_ids[:, bot_input_ids.shape[-1]:][0], skip_special_tokens=True)

# Run the Flask app
if __name__ == '__main__':
    app.run(port=port)
