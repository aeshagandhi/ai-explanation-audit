# Hi, I'm Aesha Gandhi 

**Graduate Student · Duke University (MIDS) · UC Berkeley · Data Science & Machine Learning**

I build ML and AI systems end to end — from computer vision models and agentic AI workflows to production SDKs and data pipelines. My work spans machine learning, reinforcement learning, NLP, deep learning, causal inference, and data engineering.

**Currently:**
- 🏢 Data Science Intern (Computer Vision) at **SAS**, building instance segmentation and object detection models for worker-safety pipelines (previously Applied AI Engineering and Interactive Analytics & Modeling at SAS)
- 🏦 Duke capstone with **Bank of New York**, developing agentic AI workflows for corporate action intelligence
- 🔬 Researcher at **Duke AI Trust Lab**, studying deception and misalignment in multi-agent AI systems

📍 Durham, NC &nbsp;|&nbsp; 🎓 Duke University & UC Berkeley &nbsp;|&nbsp; [LinkedIn](https://linkedin.com/in/aeshagandhi) | [Resume](Aesha_Gandhi_Resume.pdf)

---

## ⭐ Featured Projects

| Project | Description | Stack |
|---|---|---|
| [**Vision-Language-Deep-Learning**](https://github.com/aeshagandhi/Vision-Language-Deep-Learning) | Reversed the text-to-image generation paradigm by fine-tuning vision-language models (ViT-GPT2, BLIP) on 10,000 DiffusionDB image–caption pairs, achieving a 102% improvement in combined BLEU/BERTScore on NVIDIA A100 GPUs. | PyTorch · HuggingFace · ViT · BLIP |
| [**Credit-Card-Agent**](https://github.com/aeshagandhi/Credit-Card-Agent) | Agentic receipt-to-recommendation pipeline (team project; [video walkthrough](https://youtu.be/q-19Q_HRIhE)) that extracts spending patterns from receipt images using CV and OCR (Tesseract, PaddleOCR), classifies line items with a transformer-based classifier, and leverages LLM-powered web search tool use to generate grounded, real-time credit card recommendations. Compares a classical OCR + heuristic agent against a deep-learning OCR + LLM-assisted planning agent, with a Streamlit UI.<br>`ai-agents` `llm` `tool-use` `ocr` `computer-vision` `nlp` `receipt-parsing` | Python · OpenAI · Tesseract · PaddleOCR · Transformers · OpenCV · Streamlit |
| [**Codenames-Spymaster-Reinforcement-Learning**](https://github.com/aeshagandhi/Codenames-Spymaster-Reinforcement-Learning) | Goal-conditioned RL agent for the Codenames spymaster task using sentence-transformer embeddings for semantic board representation. Benchmarks Greedy, Behavioral Cloning, and Soft Actor-Critic with Hindsight Experience Replay pipelines to study imitation warm-starts and reward shaping for semantic clue generation. | Python · PyTorch · SAC · HER · Sentence Transformers |
| [**AI-Health-Agent**](https://github.com/aeshagandhi/AI-Health-Agent) | Voice-first AI companion for seniors (Duke AI Hackathon 2025). Uses OpenAI's Realtime API over WebSocket for low-latency audio, with a multi-layered prompt pipeline that converts conversation into structured assessments across 5 health dimensions with weighted severity scoring, surfaced via a family dashboard. | Python · FastAPI · React · OpenAI · Supabase · WebSockets |
| [**ai-explanation-audit**](https://github.com/aeshagandhi/ai-explanation-audit) | *Same Stakes, Different Choices?* Explainable AI audit of whether an LLM's choices and explanations hold up when a question is repeated, reworded, swapped, or challenged, using self-driving dilemmas across 820 recorded answers. The model never changed its choice under pushback (0/60), and its stated reasons matched its behavior on 92/95 answers vs. 61/95 for an "always STAY" baseline. Reproducible offline, with an interactive [live site](https://aeshagandhi.github.io/ai-explanation-audit/) and [poster](https://github.com/aeshagandhi/ai-explanation-audit/blob/main/outputs/poster/class_fair_24x36.pdf).<br>`explainable-ai` `llm-evaluation` `ai-safety` | Python · OpenAI API · Playwright |
| [**Drug-Drug-Interaction-LLM**](https://github.com/aeshagandhi/Drug-Drug-Interaction-LLM) | Drug–drug interaction prediction using fine-tuned language models. | Python · HuggingFace · Jupyter |
| [**NLP-Mental-Health-Classifier**](https://github.com/aeshagandhi/NLP-Mental-Health-Classifier) | Hybrid LDA+BERT classifier across 7 mental health categories. BERT alone (70% accuracy) outperforms complex hybrid architectures for sparse social media text. | BERT · LDA · K-Means · Scikit-learn |
| [**Music-Recommendation-Pipeline**](https://github.com/aeshagandhi/Music-Recommendation-Pipeline) | End-to-end containerized recommendation engine with two Airflow DAGs (offline ETL + online inference), pgvector embeddings, and a live Streamlit dashboard. Solves the cold-start problem with CI/CD via GitHub Actions. | Airflow · PostgreSQL · pgvector · Docker · Streamlit |

---

## 📚 Coursework & Mini Projects

Assignments and smaller projects from my Duke and Berkeley courses.

### Machine Learning (IDS 705)

| Project | Description | Stack |
|---|---|---|
| [**IDS-705-Machine-Learning**](https://github.com/aeshagandhi/IDS-705-Machine-Learning) | Coursework covering supervised/unsupervised learning, ensemble methods, model evaluation, and applied ML problem sets. | Python · Scikit-learn · NumPy · Jupyter |

### Reinforcement Learning (CompSci 590)

| Project | Description | Stack |
|---|---|---|
| [**CompSci590-ReinforcementLearning**](https://github.com/aeshagandhi/CompSci590-ReinforcementLearning) | Full RL coursework: Monte Carlo, TD learning, Q-learning, policy gradient, and CartPole feature engineering. | Python · OpenAI Gym · NumPy |

### AI & Intelligent Agents (AIPI 590)

| Project | Description | Stack |
|---|---|---|
| [**AIPI590-IntelligentAgents**](https://github.com/aeshagandhi/AIPI590-IntelligentAgents) | Projects from Duke's Intelligent Agents course including transformer implementations and agentic system design. | Python |

### Deep Learning

| Project | Description | Stack |
|---|---|---|
| [**Deep-Learning-Assignments**](https://github.com/aeshagandhi/Deep-Learning) | End-to-end deep learning coursework covering neural networks, ResNet (CIFAR-10), RNN/LSTM sequence models, GPT fine-tuning, model pruning, and adversarial attacks. | PyTorch · Transformers · CNNs · RNNs |

### Natural Language Processing (ECE 684)

| Project | Description | Stack |
|---|---|---|
| [**Natural-Language-Processing (ECE684)**](https://github.com/aeshagandhi/ECE684-Natural-Language-Processing) | NLP coursework covering Markov text generation, noisy-channel spelling correction, POS tagging, and a PyTorch unigram model for document classification, spanning probabilistic methods to neural approaches. | Python · PyTorch · NLP · Probabilistic Models |

### Data Engineering (IDS 706)

| Project | Description | Stack |
|---|---|---|
| [**DE-Kafka-Exercise**](https://github.com/aeshagandhi/DE-Kafka-Exercise) | Streaming data pipeline exercise using Apache Kafka. | Python |
| [**DE-Distributed-Data-Processing**](https://github.com/aeshagandhi/DE-Distributed-Data-Processing) | Distributed data processing patterns and implementations. | Python · Jupyter |
| [**DE-Apache-ETL-Exercise**](https://github.com/aeshagandhi/DE-Apache-ETL-Exercise) | ETL pipeline construction using Apache tooling. | Python |
| [**DE-Airflow-Exercise**](https://github.com/aeshagandhi/DE-Airflow-Exercise) | Airflow DAG design and orchestration exercises. | Python |
| [**DE-Databases**](https://github.com/aeshagandhi/DE-Databases) | Database design and management exercises. | Python |
| [**DE-Postgres-SQL-Demo**](https://github.com/aeshagandhi/DE-Postgres-SQL-Demo) | PostgreSQL in-class demo: queries, schema design, and data management. | Python · PostgreSQL |
| [**DE-Panda-Polars-DataAnalysis-Exercise**](https://github.com/aeshagandhi/DE-Panda-Polars-DataAnalysis-Exercise) | Data analysis with Pandas and Polars on a Kaggle dataset, comparing performance tradeoffs. | Python · Jupyter |
| [**DE-Python-Template-Workflow**](https://github.com/aeshagandhi/DE-Python-Template-Workflow) | Python project template with CI/CD workflow for IDS 706. | Python |

### Statistics & Causal Inference (IDS 702 / Econ)

| Project | Description | Stack |
|---|---|---|
| [**Causal-Inference-Economics-Clean-Energy**](https://github.com/aeshagandhi/Causal-Inference-Economics-Clean-Energy) | Applied causal inference methods to clean energy economics questions. Two regression studies on global energy data (OWID): carbon intensity vs. GDP per capita, and predictors of renewable energy majority. Includes GSS social class & income modeling with ordinal logistic regression. | R · Python |
| [**Statistics-Study-Guide**](https://github.com/aeshagandhi/Statistics-Study-Guide) | Personal reference covering statistical inference, regression, and hypothesis testing. | Markdown |

### Reference & Tools

| Project | Description | Stack |
|---|---|---|
| [**SQL-Guidebook**](https://github.com/aeshagandhi/SQL-Guidebook) | Personalized SQL reference built by practicing advanced queries — designed for interviews and data tasks. | SQL · Markdown |
| [**UDS-Solving-Problems-With-Data**](https://github.com/aeshagandhi/UDS-Solving-Problems-With-Data) | Applied data science problem-solving coursework. | Python · Jupyter |

---

## Skills

```
Languages      Python · R · SQL · Java
ML / DL        PyTorch · HuggingFace · Scikit-learn · NumPy · XGBoost · LightGBM
NLP / CV       BERT · LDA · ViT · BLIP · GloVe · Transformers
Data Eng       Airflow · Kafka · PostgreSQL · Docker · Streamlit · Pandas · Polars
Methods        Supervised/Unsupervised ML · RL · Causal Inference · NLP · Computer Vision
```
