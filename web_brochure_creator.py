import os
import requests
import json
from typing import List, Dict
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import streamlit as st
from openai import OpenAI

# Load environment variables
load_dotenv()
openai_api_key = os.getenv('OPENAI_API_KEY', 'your-key-if-not-using-env')
client = OpenAI(api_key=openai_api_key)

# Define prompts
LINK_SYSTEM_PROMPT = """You are provided with a list of links found on a webpage.
You are able to decide which of the links would be most relevant to include in a brochure about the company, such as links to an About page, or a Company page, or Careers/Jobs pages.
You should respond in JSON as in this example:
{
    "links": [
        {"type": "about page", "url": "https://full.url/goes/here/about"},
        {"type": "careers page": "url": "https://another.full.url/careers"}
    ]
}
"""
SYSTEM_PROMPT = """You are an assistant that analyzes the contents of several relevant pages from a company website 
and creates a short humorous, entertaining, jokey brochure about the company for prospective customers, investors, and recruits. 
Respond in markdown. Include details of company culture, customers, and careers/jobs if you have the information.
"""


class Website:
    """
    Class to represent a Website and its main contents.

    Attributes:
        url (str): The URL of the website.
        title (str): The title of the webpage.
        body (str): The raw HTML content of the webpage.
        text (str): The cleaned text content of the webpage.
        links (List[str]): A list of links found on the webpage.
    """

    def __init__(self, url: str):
        """
        Initializes a Website object and extracts the main content and links.

        Args:
            url (str): The URL of the website.
        """
        self.url = url
        response = requests.get(url)
        self.body = response.content
        soup = BeautifulSoup(self.body, 'html.parser')
        self.title = soup.title.string if soup.title else "No title found"

        # Extract text content excluding irrelevant elements
        if soup.body:
            for irrelevant in soup.body(["script", "style", "img", "input"]):
                irrelevant.decompose()
            self.text = soup.body.get_text(separator="\n", strip=True)
        else:
            self.text = ""

        # Extract and clean links
        links = [link.get('href') for link in soup.find_all('a')]
        self.links = [link for link in links if link and link.startswith('http')]

    def get_contents(self) -> str:
        """
        Returns the main contents of the website as a formatted string.

        Returns:
            str: The title and text content of the webpage.
        """
        return f"Webpage Title:\n{self.title}\nWebpage Contents:\n{self.text}\n\n"


class BrochureGenerator:
    """
    A class to generate a brochure for a company based on its website contents.

    Attributes:
        client (OpenAI): The OpenAI client to use for generating text.
    """

    def __init__(self, client: OpenAI):
        """
        Initializes a BrochureGenerator object with the specified model.

        Args:
            client (OpenAI): The OpenAI client instance.
        """
        self.client = client

    def get_links(self, url: str) -> Dict:
        """
        Extracts and filters relevant links from a website using OpenAI.

        Args:
            url (str): The URL of the website.

        Returns:
            Dict: A dictionary containing the relevant links categorized by type.
        """
        website = Website(url)
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": LINK_SYSTEM_PROMPT},
                    {"role": "user", "content": self.get_links_user_prompt(website)}
                ]
            )

            # Extract content from the response and handle JSON parsing
            content = response.choices[0].message.content

            return json.loads(content)
        except json.JSONDecodeError:
            st.error("Failed to decode JSON from the OpenAI response in get_links.")
            return {"links": []}
        except Exception as e:
            st.error(f"An error occurred in get_links: {e}")
            return {"links": []}

    def get_links_user_prompt(self, website: Website) -> str:
        """
        Generates a prompt for filtering relevant links from a website.

        Args:
            website (Website): A Website object containing the URL and links.

        Returns:
            str: The formatted user prompt with the list of links.
        """
        user_prompt = f"Here is the list of links on the website of {website.url} - "
        user_prompt += "please decide which of these are relevant web links for a brochure about the company, respond with the full https URL in JSON format. "
        user_prompt += "Do not include Terms of Service, Privacy, or email links.\n"
        user_prompt += "Links (some might be relative links):\n"
        user_prompt += "\n".join(website.links)
        return user_prompt

    def get_all_details(self, url: str) -> str:
        """
        Retrieves the main contents and relevant subpages of a website.

        Args:
            url (str): The URL of the website.

        Returns:
            str: A consolidated string of the website's main content and subpage contents.
        """
        result = f"Landing page:\n{Website(url).get_contents()}"
        links = self.get_links(url)
        for link in links["links"]:
            result += f"\n\n{link['type']}\n"
            result += Website(link["url"]).get_contents()
        return result

    def create_brochure(self, company_name: str, url: str) -> str:
        """
        Creates a brochure in markdown format based on the company name and website URL.

        Args:
            company_name (str): The name of the company.
            url (str): The URL of the company's website.

        Returns:
            str: The generated brochure in markdown format.
        """
        user_prompt = self.get_brochure_user_prompt(company_name, url)
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]
            )
            # Extract content from the response and handle JSON parsing
            content = response.choices[0].message.content

            return content
        except Exception as e:
            st.error(f"An error occurred while creating the brochure: {e}")
            return "An error occurred while generating the brochure."

    def get_brochure_user_prompt(self, company_name: str, url: str) -> str:
        """
        Generates a user prompt for creating a company brochure.

        Args:
            company_name (str): The name of the company.
            url (str): The URL of the company's website.
            url (str): The URL of the company's website.

        Returns:
            str: The formatted user prompt containing the website details.
        """
        user_prompt = f"You are looking at a company called: {company_name}\n"
        user_prompt += f"Here are the contents of its landing page and other relevant pages; use this information to build a short brochure of the company in markdown.\n"
        user_prompt += self.get_all_details(url)
        return user_prompt[:20_000]  # Truncate if more than 20,000 characters


# Streamlit Interface
def main():
    st.title("Company Brochure Generator")
    st.write("Enter the company name and URL to generate a brochure based on the website content.")

    # Input fields for company name and URL
    company_name = st.text_input("Company Name", placeholder="Enter the company name")
    company_url = st.text_input("Company URL", placeholder="Enter the company website URL")

    if st.button("Generate Brochure"):
        if company_name and company_url:
            # Create BrochureGenerator instance and generate brochure
            brochure_generator = BrochureGenerator(client)

            # Use spinner while the brochure is being generated
            with st.spinner("Generating the brochure..."):
                brochure = brochure_generator.create_brochure(company_name, company_url)

            # Display the brochure content
            st.markdown(brochure)
        else:
            st.error("Please enter both the company name and URL.")


if __name__ == "__main__":
    main()
