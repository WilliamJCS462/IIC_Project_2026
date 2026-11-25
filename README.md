# IIC_Project_2026
Repository for my UoB IIC module coursework project. A chatbot with verification and auditing tools to help bridge the AI trust gap

Current Version v1.7/docs

Tech Stack:
Python, Streamlit

Libraries:
See requirements.txt

Development Record:
V0.1 – Barebones SQL chatbot assistant
V0.2 – Basic Guardrails and Error Catching
V0.3 – UI design
V0.4 – Regression Testing (Accuracy Score Tests)
V1.0 – Accuracy Score
V1.1 – Complexity Score
V1.2 – Query Details
V1.3 – Drill Down
V1.4 – Expanded Context
V1.5 – Logging
V1.6 – Secondary Auditing
V1.7 - Docs

Running Locally
The only additional file needed is a .env file with one field:
- OPENAI_API_KEY=
This needs to contain OpenAI API key for the chatbot to use for LLM calls
Once requirements.txt has been installed, the code can be started from the root folder using:
- streamlit run app.py
