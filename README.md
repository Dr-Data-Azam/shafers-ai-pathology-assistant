# 🦷 Shafer's Oral Pathology Q&A System

A comprehensive RAG (Retrieval Augmented Generation) system that provides accurate answers to oral pathology questions based exclusively on **Shafer's Textbook of Oral Pathology (7th Edition)**.

![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-v1.28+-red.svg)
![LangChain](https://img.shields.io/badge/langchain-v0.1+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## About

This application uses advanced AI techniques to answer questions about oral medicine, diagnosis, and pathology based on the authoritative Shafer's textbook. It employs vector similarity search and large language models to provide accurate, contextual answers with page references.

### Key Features

- **Accurate Answers**: Based exclusively on Shafer's Textbook content
- **Multiple AI Models**: Support for OpenAI GPT-4o and Groq Llama models
- **Page References**: Answers include specific page numbers from the textbook
- **Intelligent Retrieval**: Uses advanced RAG techniques for comprehensive responses
- **Chat History**: Persistent conversation history with performance analytics
- **Clean UI**: Modern Streamlit interface with dark mode support

## Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key or Groq API key
- Shafer's Textbook of Oral Pathology (7th Edition) PDF

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/shafers-oral-pathology-qa.git
   cd shafers-oral-pathology-qa
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   # Create .env file
   echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
   echo "GROQ_API_KEY=your_groq_api_key_here" >> .env
   ```

4. **Add your PDF**
   ```bash
   mkdir data
   # Place your Shafer's textbook PDF in the data/ folder
   ```

5. **Create vector database**
   ```bash
   python vector_store_creator.py
   ```

6. **Run the application**
   ```bash
   streamlit run streamlit_app.py
   ```

## Project Structure

```
MED-BOT/
├── README.md
├── streamlit_app.py              # Main Streamlit application
├── rag_system.py                 # Core RAG functionality
├── llm_provider_manager.py       # LLM provider management
├── vector_retriever.py           # Document retrieval logic
├── chat_history_manager.py       # Chat history operations
├── vector_store_creator.py       # Vector database creation
├── main_console.py               # Console interface 
├── requirements.txt              # Python dependencies
├── .gitignore  
├── .env                          # Environment variables 
├── data/                         # PDF files directory
│   └── shafers_textbook.pdf      # Your Shafer's textbook PDF
├── vectorDB/                     # Generated vector database
└── chat_history.json             # Persistent chat history
```

## Configuration

### API Keys

You can use either OpenAI or Groq (or both):

**OpenAI API Key:**
- Go to [platform.openai.com](https://platform.openai.com)
- Create an account and generate an API key
- Add to `.env` file: `OPENAI_API_KEY=sk-...`

**Groq API Key:**
- Go to [console.groq.com](https://console.groq.com)
- Create an account and generate an API key
- Add to `.env` file: `GROQ_API_KEY=gsk_...`

### Model Comparison

| Provider | Model | Speed | Quality | Cost |
|----------|-------|-------|---------|------|
| OpenAI | GPT-4o | Medium | Excellent | Higher |
| Groq | Llama 3.1 70B | Fast | Very Good | Lower |

## Usage Examples

### Specific Questions
```
Q: "Enlist tooth development anomalies"
A: Returns a numbered list of developmental anomalies with page references

Q: "Define oral leukoplakia"
A: Provides precise definition from the textbook
```

### General Concepts
```
Q: "Explain oral cancer"
A: Comprehensive coverage including etiology, clinical features, diagnosis, treatment

Q: "What is the difference between benign and malignant tumors?"
A: Detailed comparison with distinguishing features
```

### Classifications
```
Q: "Classify oral tumors"
A: Complete classification system as per Shafer's textbook
```

## User Interface

### Main Features
- **Clean Question Input**: Large text area for questions
- **AI Model Selection**: Choose between OpenAI and Groq
- **Sample Questions**: Quick-start with pre-loaded questions
- **Real-time Stats**: Response time and pages retrieved
- **Chat Tabs**: Current session and persistent history

### Sample Questions Available
- What are tooth development anomalies?
- Explain the classification of oral tumors
- What are the clinical features of oral cancer?
- Describe the pathogenesis of dental caries
- What is the difference between hyperplasia and hypertrophy?

## Technical Details

### RAG Architecture
1. **Document Processing**: PDF split into chunks with metadata
2. **Vector Embeddings**: Using HuggingFace sentence-transformers
3. **Retrieval**: FAISS vector database with MMR search
4. **Context Enhancement**: Multi-query expansion for comprehensive coverage
5. **Generation**: Adaptive prompting based on question type

### Performance Optimizations
- **Caching**: LLM instances and retriever cached for speed
- **Batch Processing**: Efficient vector database creation
- **Smart Retrieval**: Dynamic document selection based on query
- **Error Handling**: Graceful fallbacks and user-friendly messages

## Development

### Running Tests
```bash
# Test vector database creation
python vector_store_creator.py

# Test console interface
python main_console.py test

# Test both providers
python main_console.py
```

### Adding New Features
1. **New Retrievers**: Extend `vector_retriever.py`
2. **New Providers**: Add to `llm_provider_manager.py`
3. **UI Components**: Modify `streamlit_app.py`
4. **History Features**: Extend `chat_history_manager.py`

## Deployment

### Local Deployment
```bash
# Run with external access
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```

### Cloud Deployment
- **Streamlit Cloud**: Connect GitHub repo and deploy
- **Hugging Face Spaces**: Upload files and deploy as Streamlit app
- **Heroku/Railway**: Use provided Dockerfile

## Requirements

```txt
streamlit>=1.28.0
langchain>=0.1.0
langchain-community>=0.0.20
langchain-openai>=0.0.5
langchain-groq>=0.0.1
langchain-huggingface>=0.0.1
faiss-cpu>=1.7.4
sentence-transformers>=2.2.2
pypdf>=3.17.0
plotly>=5.17.0
pandas>=2.0.0
python-dotenv>=1.0.0
numpy>=1.24.0
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request


## Legal Notice

This application is designed for educational and research purposes. Users must:
- Own a legitimate copy of Shafer's Textbook of Oral Pathology (7th Edition)
- Comply with copyright laws and fair use guidelines
- Not redistribute the textbook content
- Use the system responsibly for learning and professional development


## Citation

If you use this system in your research or education, please cite:

```
Shafer's Oral Pathology Q&A System
Based on: Shafer's Textbook of Oral Pathology (7th Edition)
Authors: Shafer, Hine, Levy
Editors: R Rajendran, B Sivapathasundharam
Publisher: Elsevier
```


**Built with ❤️ for dental education and research**

*Empowering dental professionals and students with AI-powered access to authoritative oral pathology knowledge.*