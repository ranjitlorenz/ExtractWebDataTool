from flask import Flask, request, render_template_string
import requests
from bs4 import BeautifulSoup
from newspaper import Article # Import Newspaper3k
import os

app = Flask(__name__)

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>News Article Extractor</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background-color: #f4f4f4; 
            color: #333; 
        }
        .container { 
            max-width: 800px; 
            margin: auto; 
            padding: 20px; 
            border: 1px solid #ccc; 
            border-radius: 8px; 
            background-color: #fff; 
            box-shadow: 0 0 10px rgba(0,0,0,0.1); 
        }
        h1 { 
            color: #007bff; 
            text-align: center; 
            margin-bottom: 25px; 
        }
        h2 { 
            color: #555; 
            border-bottom: 1px solid #eee; 
            padding-bottom: 10px; 
            margin-top: 30px; 
        }
        input[type="text"] { 
            width: calc(100% - 22px); 
            padding: 10px; 
            margin-bottom: 15px; 
            border: 1px solid #ddd; 
            border-radius: 4px; 
            box-sizing: border-box;
        }
        button { 
            padding: 10px 20px; 
            background-color: #28a745; 
            color: white; 
            border: none; 
            border-radius: 5px; 
            cursor: pointer; 
            font-size: 16px; 
            transition: background-color 0.3s ease; 
        }
        button:hover { 
            background-color: #218838; 
        }
        
        .result-section {
            margin-top: 25px; 
            padding: 15px; 
            background-color: #e9f7ef; 
            border: 1px solid #d4edda; 
            border-radius: 6px; 
        }
        .result-section h3 {
            color: #333;
            margin-top: 0;
            margin-bottom: 10px;
            border-bottom: 1px dashed #c0e0c0;
            padding-bottom: 5px;
        }
        .result-content {
            white-space: pre-wrap; /* Preserve whitespace and line breaks */
            word-wrap: break-word; /* Break long words */
            font-size: 14px;
            line-height: 1.6;
            max-height: 400px;
            overflow-y: auto;
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 4px;
            border: 1px solid #eee;
        }

        .error { 
            margin-top: 25px; 
            padding: 15px; 
            background-color: #f8d7da; 
            border: 1px solid #f5c6cb; 
            border-radius: 6px; 
            color: #721c24; 
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>News Article Extractor</h1>

        <h2>Enter Article URL</h2>
        <form method="post" action="/extract-article">
            <input type="text" name="url" placeholder="e.g., https://www.thehindu.com/news/article-headline-url" required>
            <button type="submit">Extract Article</button>
        </form>

        {% if error_message %}
        <div class="error">
            <h3>Error:</h3>
            <p>{{ error_message }}</p>
        </div>
        {% endif %}

        {% if extracted_article_content %}
        <div class="result-section">
            <h3>Extracted Content from: <a href="{{ extracted_url }}" target="_blank">{{ extracted_url }}</a></h3>
            <div class="result-content">{{ extracted_article_content }}</div>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    """Renders the main page with the URL input form."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/extract-article', methods=['POST'])
def extract_article():
    """Handles URL input and extracts news article content."""
    url = request.form['url']
    if not url:
        return render_template_string(HTML_TEMPLATE, error_message="Please enter a URL.")

    # Basic URL validation (prepend https:// if missing)
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url

    extracted_text = ""
    error_msg = None

    try:
        # --- Attempt to use Newspaper3k first ---
        article = Article(url)
        article.download()
        article.parse()
        
        if article.text.strip():
            extracted_text = article.text
        else:
            # Fallback to BeautifulSoup if Newspaper3k finds no significant text
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find common article content containers
            content_divs = soup.find_all(['article', {'div': ['article-body', 'post-content', 'entry-content', 'main-content', 'td_block_wrap td_block_single_content']}, 'main'])
            
            combined_paragraphs = []
            if content_divs:
                for div in content_divs:
                    paragraphs = div.find_all('p')
                    filtered_paragraphs = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50]
                    if filtered_paragraphs:
                        combined_paragraphs.extend(filtered_paragraphs)
                
            if combined_paragraphs:
                extracted_text = "\n\n".join(combined_paragraphs)
            else:
                # Last resort: get all paragraphs if no specific article content found
                all_paragraphs = soup.find_all('p')
                extracted_text = "\n\n".join([p.get_text(strip=True) for p in all_paragraphs if p.get_text(strip=True)])
                if not extracted_text:
                     error_msg = "No text content found. The page might be empty, heavily JavaScript-driven, or blocked scraping."


    except requests.exceptions.RequestException as e:
        error_msg = f"Network or URL error: {e}. Please check the URL and your internet connection. (Note: Some sites block automated requests.)"
    except Exception as e:
        error_msg = f"An unexpected error occurred during extraction: {e}. The website structure might be too complex or an internal server error occurred."

    if error_msg:
        return render_template_string(HTML_TEMPLATE, error_message=error_msg)
    elif extracted_text:
        return render_template_string(HTML_TEMPLATE, extracted_article_content=extracted_text, extracted_url=url)
    else:
        return render_template_string(HTML_TEMPLATE, error_message="Could not extract any meaningful content from the provided URL. It might not be a text-heavy article page, or its structure is not recognized.")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 5000))