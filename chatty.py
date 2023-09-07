from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer
import spacy
import sys

# Load the spaCy model
nlp = spacy.load('en_core_web_sm')

# Initialize the chatbot
chatbot = ChatBot(
    'AlphaBot',
    storage_adapter='chatterbot.storage.SQLStorageAdapter',
    database_uri='sqlite:///database.sqlite3'
)

# Manually set the tagger's NLP model
chatbot.storage.tagger.nlp = nlp

# Use a corpus trainer
trainer = ChatterBotCorpusTrainer(chatbot)
trainer.train('chatterbot.corpus.english')

# Main conversation loop
while True:
    user_input = input("You: ")
    if user_input.lower() == 'quit':
        break
    response = chatbot.get_response(user_input)
    print(f"AlphaBot: {response}")

print("Python interpreter location:", sys.executable)
