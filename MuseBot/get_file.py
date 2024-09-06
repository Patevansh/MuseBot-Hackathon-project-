import fitz
import requests
from bs4 import BeautifulSoup


def extract_pdf_text(pdf_file):
    text = ""
    try:
        doc = fitz.open(pdf_file)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text()
        doc.close()
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
    return text


def fetch_webpage_content(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            paragraphs = soup.find_all('p')
            content = ' '.join([p.get_text() for p in paragraphs])
            return content
        else:
            return None
    except Exception as e:
        print(f"Error fetching webpage: {str(e)}")
        return None