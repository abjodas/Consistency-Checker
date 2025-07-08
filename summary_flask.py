from flask import Flask, request, jsonify, render_template_string
import re
from openai import OpenAI


# Initialize the Flask application
app = Flask(__name__)

# HTML and JavaScript template.
# Using render_template_string allows Flask to serve this directly.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Consistency Checker</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <h1>Document and Summary Consistency Checker</h1>
    <p class="description">
        Enter a document and its summary below to verify factual consistency. 
        A summary is considered consistent if all its claims are supported by information present in the article, with no new details added.
    </p>
    <div class="input-group">
    <div class="label-container">
        <img src="{{ url_for('static', filename='icons/doc_icon.svg') }}" alt="Document Icon" class="label-icon">
        
        <label for="document">Document</label>
    </div>
</div>
    <textarea id="document" placeholder="Paste the full document here..." style="width: 100%; height: 150px;"></textarea>
    <div class="input-group">
    <div class="label-container">
        <img src="{{ url_for('static', filename='icons/sum_icon.svg') }}" alt="Summary Icon" class="label-icon">
        
        <label for="document">Summary</label>
    </div>
    </div>
    <textarea id="summary" placeholder="Paste the summary here..." style="width: 100%; height: 100px;"></textarea>
    <button onclick="checkConsistency()">Check Consistency</button>
    <div id="result" style="margin-top: 20px;"></div>

    <script>
        async function checkConsistency() {
            const documentText = document.getElementById('document').value;
            const summaryText = document.getElementById('summary').value;
            const resultDiv = document.getElementById('result');
            
            resultDiv.innerHTML = 'Checking...';
            resultDiv.style.display = 'block';

            // This fetch request will now correctly go to
            // http://127.0.0.1:5000/check_consistency
            const response = await fetch('/check_consistency', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    document: documentText,
                    summary: summaryText,
                }),
            });

            const result = await response.json();

            if (response.ok) {
                resultDiv.innerHTML = `
                    <h3>Verdict: ${result.verdict}</h3>
                    <p><b>Reasoning:</b> ${result.reasoning}</p>
                `;
            } else {
                resultDiv.innerHTML = `<p style="color:red;"><b>Error:</b> ${result.error}</p>`;
            }
        }
    </script>
</body>
</html>
"""
# Helper functions


def extract_answer_qwen(text: str) -> int:
  pattern1 = r'\bAnswer:\sconsistent\b'
  pattern2 = r'\bFinal\sAnswer:\sconsistent\b'
  pattern3 = r'\bAnswer:\s\*\*consistent\*\*'
  pattern4 = r'\*\*Final\sAnswer:\sconsistent\*\*'
  pattern5 = r'\*\*Final\sanswer:\sconsistent\*\*'
  pattern6 = r'\bAnswer:\s\*\*Consistent\*\*'
  pattern7 = r'\b\*\*Answer:\*\*\n\*\*Consistent\*\*'
  pattern8 = r'\*\*Final\sanswer:\sConsistent\*\*'
  pattern9 = r'\bAnswer:\nconsistent'
  pattern10 = r'\bAnswer:\nConsistent'
  pattern11 = r'\*\*Answer:\*\*\s\*\*Consistent\*\*'
  pattern12 = r'\*\*Answer:\*\*\sConsistent'
  pattern12 = r'\*\*Answer:\*\*\sconsistent'
  pattern13 = r'\*\*Answer:\sconsistent\*\*'
  pattern14 = r'\*\*Answer:\sConsistent\*\*'
  pattern15 = r'Answer:\s\s\n\*\*Consistent\*\*'
  pattern16 = r'(\*\*(c|C)onsistency\*\*){1}$'
  pattern17 = r'(\b(c|C)onsistent){1}$'
  pattern18 = r'(\*\*(c|C)onsistent)\*\*{1}$'
  pattern19 = r'\bAnswer:\sconsistent\b'
  pattern20 = r'\bFinal\sAnswer:\sconsistent\b'
  pattern21 = r'\bAnswer:\s\*\*consistent\*\*'
  pattern22 = r'\*\*Final\sAnswer:\sconsistent\*\*'
  pattern23 = r'\*\*Final\sanswer:\sconsistent\*\*'
  pattern24 = r'\bAnswer:\s\*\*Consistent\*\*'
  pattern25 = r'\b\*\*Answer:\*\*\n\*\*Consistent\*\*'
  pattern26 = r'\*\*Final\sanswer:\sConsistent\*\*'
  pattern27 = r'\bAnswer:\nconsistent'
  pattern28 = r'\bAnswer:\nConsistent'
  pattern29 = r'\*\*Answer:\*\*\s\*\*Consistent\*\*'
  pattern30 = r'\*\*Answer:\*\*\sConsistent'
  pattern31 = r'\*\*Answer:\*\*\sconsistent'
  pattern32 = r'\*\*Answer:\sconsistent\*\*'
  pattern33 = r'\*\*Answer:\sConsistent\*\*'
  pattern34 = r'Answer:\s\s\n\*\*Consistent\*\*'
  pattern35 = r'(\*\*(c|C)onsistency\*\*){1}$'
  pattern36 = re.compile(
    r'^\*\*Answer\*\*:\s*Consistent\.\s*\Z',  # \Z = absolute end of string
    re.MULTILINE | re.IGNORECASE
)

  if re.search(pattern1, text) or re.search(pattern2, text) or re.search(pattern3, text)or re.search(pattern4, text)\
  or re.search(pattern5, text) or re.search(pattern6, text) or re.search(pattern7, text) or re.search(pattern9, text)\
  or re.search(pattern10, text) or re.search(pattern11, text) or re.search(pattern12, text) or re.search(pattern13, text)\
  or re.search(pattern14, text) or re.search(pattern15, text) or re.search(pattern16, text) or re.search(pattern17, text)\
  or re.search(pattern18, text) or re.search(pattern19, text) or re.search(pattern20, text) or re.search(pattern21, text)or re.search(pattern22, text)\
  or re.search(pattern23, text) or re.search(pattern24, text) or re.search(pattern25, text) or re.search(pattern26, text)\
  or re.search(pattern27, text) or re.search(pattern28, text) or re.search(pattern29, text) or re.search(pattern30, text)\
  or re.search(pattern31, text) or re.search(pattern32, text) or re.search(pattern33, text) or re.search(pattern34, text)\
  or re.search(pattern35, text) or re.search(pattern36, text):
    return 1
  else:
    return 0
  
def check_consistency(document: str, summary: str) -> dict:
    """
    Function to check the consistency of a summary with a document.
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    messages = [
       {"role": "system", "content": "You are a helpful assistant"},
          {"role": "user", "content": f"""Decide if the following summary is consistent with the corresponding article. 
      Note that consistency means all information in the summary is supported by the article.
      Explain your reasoning step by step first, and then answer (consistent or inconsistent) at the end:
      <Article>
      {document}
      </Article>

      <Summary>
      {summary}
      </Summary>

      Answer:
      """},
    ]
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        stream = False 
    )
    response_text = response.choices[0].message.content.strip()
    verdict = "consistent" if extract_answer_qwen(response_text) == 1 else "inconsistent"
    return {
        'reasoning': response_text,
        'verdict': verdict
    }
# Route to serve the main HTML page
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# Route for your API endpoint
@app.route('/check_consistency', methods=['POST'])
def check_consistency_endpoint():
    data = request.get_json()
    if not data or not data.get('document') or not data.get('summary'):
        return jsonify({'error': 'Document and summary are required.'}), 400

    answer = check_consistency(data['document'], data['summary'])
    
    return jsonify({
        'reasoning': answer['reasoning'],
        'verdict': answer['verdict']
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
