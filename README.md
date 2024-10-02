# Web brochure creator
LLM solution to create a brochure base on the website of a company. The result is shown in markdown format.

## Run code
Create a virtual env and install all the packages in requirements.txt:

    pip install -r requirements.txt

Create a .env file with the following content:
    
    OPENAI_API_KEY=<API_KEY>
    

OpenAI API key could be generated in the following way:
https://gptforwork.com/help/knowledge-base/create-openai-api-key


Execute the following command:

    streamlit run web_brochure_creator.py

