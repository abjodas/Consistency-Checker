from flask import Flask, request, jsonify, render_template_string
import re
from openai import OpenAI


# Initialize the Flask application
app = Flask(__name__)

# HTML and JavaScript template.
# Using render_template_string allows Flask to serve this directly.


NAV_BAR = """
<nav class="navbar">
    <a href="/" class="nav-link {% if active_page == 'consistency' %}active{% endif %}">Consistency Checker</a>
    <a href="/rank" class="nav-link {% if active_page == 'ranking' %}active{% endif %}">Summary Ranker</a>
</nav>
"""

# RANKING_PAGE_HTML ="""
# <!DOCTYPE html>
# <html lang="en">
# <head>
#     <meta charset="UTF-8">
#     <title>Summary Ranker</title>
#     <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
# </head>
# <body>
# """ +  NAV_BAR + """
# <div class="container">
#     <h1>Rank Summaries by Quality</h1>
#     <p class="description">Provide one document and multiple summaries. The model will rank the summaries from best to worst based on accuracy and coverage.</p>
    
#     <div class="input-group">
#         <label for="document">Document</label>
#         <textarea id="document" placeholder="Paste the full document here..." rows="10"></textarea>
#     </div>

#     <div id="summaries-container">
#         <div class="input-group summary-entry">
#             <label>Summary 1</label>
#             <textarea class="summary-text" placeholder="Paste summary here..." rows="3"></textarea>
#         </div>
#     </div>
    
#     <button type="button" id="add-summary-btn">Add Another Summary</button>
#     <button type="button" id="rank-btn">Rank Summaries</button>
    
#     <div id="result"></div>
# </div>
# <script>
# document.getElementById('add-summary-btn').addEventListener('click', function() {
#     const container = document.getElementById('summaries-container');
#     const newIndex = container.children.length + 1;
#     const newSummary = document.createElement('div');
#     newSummary.className = 'input-group summary-entry';
#     newSummary.innerHTML = `
#         <label>Summary ${newIndex}</label>
#         <textarea class="summary-text" placeholder="Paste summary here..." rows="3"></textarea>
#     `;
#     container.appendChild(newSummary);
# });

# document.getElementById('rank-btn').addEventListener('click', async function() {
#     const documentText = document.getElementById('document').value;
#     const summaryElements = document.querySelectorAll('.summary-text');
#     const summaries = Array.from(summaryElements).map(s => s.value);
#     const resultDiv = document.getElementById('result');

#     resultDiv.style.display = 'block';
#     resultDiv.innerHTML = 'Ranking...';

#     const response = await fetch('/rank_summaries', {
#         method: 'POST',
#         headers: { 'Content-Type': 'application/json' },
#         body: JSON.stringify({ document: documentText, summaries: summaries }),
#     });

#     const result = await response.json();
#     resultDiv.innerHTML = `<h3>Ranked Summaries:</h3><pre>${result.ranking}</pre>`;
# });
# </script>
# """

RANKING_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Summary Ranker</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <style>
        .summary-entry {
            transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1);
            transform-origin: center;
            position: relative;
            overflow: hidden;
        }
        
        .summary-entry.ranking {
            transform: scale(0.98);
            opacity: 0.7;
            pointer-events: none;
        }
        
        .summary-entry.moving {
            z-index: 10;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
            transform: scale(1.02);
        }
        
        .summary-entry.final-position {
            animation: highlight 1s ease-in-out;
        }
        
        @keyframes highlight {
            0% { background-color: #f8f9fa; }
            50% { background-color: #e3f2fd; }
            100% { background-color: #ffffff; }
        }
        
        .rank-badge {
            position: absolute;
            top: 10px;
            right: 10px;
            background: linear-gradient(45deg, #B33791, #DB8DD0);
            color: white;
            border-radius: 20px;
            padding: 5px 12px;
            font-size: 12px;
            font-weight: bold;
            opacity: 0;
            transform: scale(0);
            transition: all 0.3s ease;
        }
        
        .rank-badge.show {
            opacity: 1;
            transform: scale(1);
        }
        
        .ranking-explanation {
            background: #f8f9fa;
            border-left: 4px solid #B33791;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            white-space: pre-wrap;
            line-height: 1.4;
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.5s ease;
        }
        
        .ranking-explanation.show {
            opacity: 1;
            transform: translateY(0);
        }
        
        .progress-bar {
            width: 100%;
            height: 4px;
            background-color: #e0e0e0;
            border-radius: 2px;
            overflow: hidden;
            margin: 20px 0;
            display: none;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #B33791, #DB8DD0);
            border-radius: 2px;
            transition: width 0.3s ease;
            width: 0%;
        }
        
        .summary-container {
            position: relative;
        }
    </style>
</head>
<body>
""" + NAV_BAR + """
<div class="container">
    <h1>Rank Summaries by Quality</h1>
    <p class="description">Provide one document and multiple summaries. The AI will rank them from best to worst based on accuracy, completeness, and consistency.</p>
    
    <div class="input-group">
        <label for="document">Document</label>
        <textarea id="document" placeholder="Paste the full document here..." rows="10"></textarea>
    </div>

    <div id="summaries-container" class="summary-container">
        <div class="input-group summary-entry" data-original-index="0">
            <label>Summary 1</label>
            <textarea class="summary-text" placeholder="Paste summary here..." rows="3"></textarea>
            <div class="rank-badge"></div>
        </div>
    </div>
    
    <button type="button" id="add-summary-btn">Add Another Summary</button>
    <button type="button" id="rank-btn">Rank Summaries</button>
    
    <div class="progress-bar">
        <div class="progress-fill"></div>
    </div>
    
    <div id="result"></div>
</div>
<script>
let summaryCount = 1;
let isRanking = false;

document.getElementById('add-summary-btn').addEventListener('click', function() {
    if (isRanking) return;
    
    const container = document.getElementById('summaries-container');
    summaryCount++;
    const newSummary = document.createElement('div');
    newSummary.className = 'input-group summary-entry';
    newSummary.setAttribute('data-original-index', summaryCount - 1);
    newSummary.innerHTML = `
        <label>Summary ${summaryCount}</label>
        <textarea class="summary-text" placeholder="Paste summary here..." rows="3"></textarea>
        <div class="rank-badge"></div>
    `;
    container.appendChild(newSummary);
});

document.getElementById('rank-btn').addEventListener('click', async function() {
    if (isRanking) return;
    
    const documentText = document.getElementById('document').value.trim();
    const summaryElements = document.querySelectorAll('.summary-text');
    const summaries = Array.from(summaryElements).map(s => s.value.trim()).filter(s => s);
    
    if (!documentText) {
        alert('Please provide a document to analyze.');
        return;
    }
    
    if (summaries.length < 2) {
        alert('Please provide at least 2 summaries to rank.');
        return;
    }
    
    isRanking = true;
    const resultDiv = document.getElementById('result');
    const progressBar = document.querySelector('.progress-bar');
    const progressFill = document.querySelector('.progress-fill');
    const rankBtn = document.getElementById('rank-btn');
    
    // Reset previous results
    resultDiv.innerHTML = '';
    document.querySelectorAll('.rank-badge').forEach(badge => {
        badge.classList.remove('show');
        badge.textContent = '';
    });
    
    // Show progress and update button
    progressBar.style.display = 'block';
    rankBtn.textContent = 'Analyzing...';
    rankBtn.disabled = true;
    
    // Add ranking class to all summaries
    document.querySelectorAll('.summary-entry').forEach(entry => {
        entry.classList.add('ranking');
    });
    
    // Simulate progress
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 90) progress = 90;
        progressFill.style.width = progress + '%';
    }, 200);
    
    try {
        const response = await fetch('/rank_summaries', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ document: documentText, summaries: summaries }),
        });
        
        const result = await response.json();
        
        clearInterval(progressInterval);
        progressFill.style.width = '100%';
        
        setTimeout(() => {
            progressBar.style.display = 'none';
            if (result.success) {
                displayRankingResults(result.ranking_order, result.explanation);
            } else {
                resultDiv.innerHTML = `<p style="color:red;"><b>Error:</b> ${result.error}</p>`;
            }
            
            rankBtn.textContent = 'Rank Summaries';
            rankBtn.disabled = false;
            isRanking = false;
        }, 500);
        
    } catch (error) {
        clearInterval(progressInterval);
        progressBar.style.display = 'none';
        resultDiv.innerHTML = `<p style="color:red;"><b>Error:</b> ${error.message}</p>`;
        rankBtn.textContent = 'Rank Summaries';
        rankBtn.disabled = false;
        isRanking = false;
        
        // Remove ranking class
        document.querySelectorAll('.summary-entry').forEach(entry => {
            entry.classList.remove('ranking');
        });
    }
});

function displayRankingResults(rankingOrder, explanation) {
    const container = document.getElementById('summaries-container');
    const summaryEntries = Array.from(container.querySelectorAll('.summary-entry'));
    
    // Remove ranking class and add moving class
    summaryEntries.forEach(entry => {
        entry.classList.remove('ranking');
        entry.classList.add('moving');
    });
    
    // Create a new order based on ranking
    const reorderedEntries = rankingOrder.map(index => summaryEntries[index]);
    
    // Animate the reordering
    setTimeout(() => {
        // Clear container
        container.innerHTML = '';
        
        // Add entries in new order with animation
        reorderedEntries.forEach((entry, newIndex) => {
            const rankBadge = entry.querySelector('.rank-badge');
            const label = entry.querySelector('label');
            
            // Update label and rank badge
            label.textContent = `Summary ${newIndex + 1} (Rank #${newIndex + 1})`;
            rankBadge.textContent = `#${newIndex + 1}`;
            
            // Remove moving class and add final position
            entry.classList.remove('moving');
            entry.classList.add('final-position');
            
            container.appendChild(entry);
            
            // Show rank badge with delay
            setTimeout(() => {
                rankBadge.classList.add('show');
            }, newIndex * 100);
        });
        
        // Show explanation
        const resultDiv = document.getElementById('result');
        resultDiv.innerHTML = `
            <div class="ranking-explanation">
                <h3>🏆 Ranking Analysis</h3>
                ${explanation}
            </div>
        `;
        
        setTimeout(() => {
            resultDiv.querySelector('.ranking-explanation').classList.add('show');
        }, 100);
        
        // Clean up classes after animation
        setTimeout(() => {
            summaryEntries.forEach(entry => {
                entry.classList.remove('final-position');
            });
        }, 2000);
        
    }, 300);
}
</script>
</body>
</html>
"""



CONSISTENCY_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Consistency Checker</title>
    <style>
        /* A modern, clean look for the whole page */
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f4f7f6;
            color: #333;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
        }

        /* Center the main content */
        .container {
            max-width: 800px;
            margin: 20px auto;
            background: #ffffff;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }

        h1 {
            color: #B33791;
            text-align: center;
            margin-bottom: 30px;
        }

        .input-group {
            margin-bottom: 20px;
        }

        .label-container {
            display: flex;
            align-items: center;
            margin-bottom: 8px;
        }

        .label-icon {
            width: 24px;
            height: 24px;
            margin-right: 8px;
            color: #555; 
        }

        label {
            font-size: 18px;
            font-weight: 500;
            color: #333;
        }

        textarea {
            width: 100%;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #ccc;
            margin-bottom: 20px;
            font-size: 16px;
            box-sizing: border-box;
            transition: border-color 0.3s, box-shadow 0.3s;
        }

        textarea:focus {
            outline: none;
            border-color: #DB8DD0;
            box-shadow: 0 0 5px rgba(179, 55, 145);
        }

        .description {
            text-align: center;
            color: #555;
            font-size: 16px;
            margin-top: -15px;
            margin-bottom: 30px;
            font-family: 'Courier New', Courier, monospace;
            line-height: 1.5;
        }

        button {
            display: block;
            width: 100%;
            padding: 12px 24px;
            border: 1px solid #2980b9;
            background-image: linear-gradient(to right, #B33791, #DB8DD0);
            color: #ffffff;
            font-size: 20px;
            font-weight: 1000;
            border-radius: 12px;
            cursor: pointer;
            font-family: 'Franklin Gothic Medium', 'Arial Narrow', Arial, sans-serif;
            background-size: 200% auto;
            transition: all 0.4s ease-in-out;
            position: relative;
            overflow: hidden;
        }

        button:hover:not(:disabled) {
            background-position: right center;
        }

        button:disabled {
            opacity: 0.7;
            cursor: not-allowed;
        }

        #result {
            display: none;
            margin-top: 30px;
            padding: 20px;
            background: #ecf0f1;
            border-left: 5px solid #B33791;
            border-radius: 5px;
        }

        #result h3 {
            margin-top: 0;
        }

        /* Loading Animation Styles */
        .loading-container {
            display: none;
            text-align: center;
            margin-top: 30px;
            padding: 30px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 15px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }

        .loading-spinner {
            width: 60px;
            height: 60px;
            border: 4px solid #e3f2fd;
            border-top: 4px solid #B33791;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .loading-text {
            font-size: 18px;
            font-weight: 500;
            color: #B33791;
            margin-bottom: 20px;
        }

        .loading-text::after {
            content: '';
            animation: dots 1.5s infinite;
        }

        @keyframes dots {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60% { content: '...'; }
            80%, 100% { content: ''; }
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background-color: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 15px;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #B33791, #DB8DD0);
            border-radius: 4px;
            transition: width 0.3s ease;
            width: 0%;
            animation: shimmer 2s infinite;
        }

        @keyframes shimmer {
            0% { background-position: -200px 0; }
            100% { background-position: 200px 0; }
        }

        .progress-fill {
            background: linear-gradient(90deg, #B33791 25%, #DB8DD0 50%, #B33791 75%);
            background-size: 200px 100%;
        }

        .step-indicator {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 15px;
            font-size: 14px;
            color: #666;
        }

        .step {
            display: flex;
            align-items: center;
            opacity: 0.5;
            transition: opacity 0.3s ease;
        }

        .step.active {
            opacity: 1;
            color: #B33791;
            font-weight: 600;
        }

        .step-icon {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #e0e0e0;
            margin-right: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            transition: background 0.3s ease;
        }

        .step.active .step-icon {
            background: #B33791;
            color: white;
        }

        .step.completed .step-icon {
            background: #4CAF50;
            color: white;
        }

        .step.completed .step-icon::after {
            content: '✓';
        }

        .navbar {
            background-color: #ffffff;
            padding: 0 20px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            margin-bottom: 30px;
            display: flex;
            justify-content: center;
        }

        .nav-link {
            padding: 15px 20px;
            text-decoration: none;
            color: #555;
            font-weight: 500;
            transition: color 0.3s;
        }

        .nav-link:hover {
            color: #DB8DD0;
        }

        .nav-link.active {
            color: #B33791;
            border-bottom: 3px solid #B33791;
        }
    </style>
</head>
<body>
    """ + NAV_BAR + """
    <div class="container">
        <h1>Document and Summary Consistency Checker</h1>
        <p class="description">
            Enter a document and its summary below to verify factual consistency. 
            A summary is considered consistent if all its claims are supported by information present in the article, with no new details added.
        </p>
        
        <div class="input-group">
            <div class="label-container">
                <svg class="label-icon" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
                </svg>
                <label for="document">Document</label>
            </div>
            <textarea id="document" placeholder="Paste the full document here..." rows="8"></textarea>
        </div>

        <div class="input-group">
            <div class="label-container">
                <svg class="label-icon" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M14,17H7V15H14M17,13H7V11H17M17,9H7V7H17M19,3H5C3.89,3 3,3.89 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5C21,3.89 20.1,3 19,3Z"/>
                </svg>
                <label for="summary">Summary</label>
            </div>
            <textarea id="summary" placeholder="Paste the summary here..." rows="5"></textarea>
        </div>

        <button id="check-btn">Check Consistency</button>
        
        <div id="loading" class="loading-container">
            <div class="loading-spinner"></div>
            <div class="loading-text">Analyzing consistency</div>
            <div class="progress-bar">
                <div class="progress-fill"></div>
            </div>
            <div class="step-indicator">
                <div class="step" id="step1">
                    <div class="step-icon">1</div>
                    <span>Reading Document</span>
                </div>
                <div class="step" id="step2">
                    <div class="step-icon">2</div>
                    <span>Analyzing Summary</span>
                </div>
                <div class="step" id="step3">
                    <div class="step-icon">3</div>
                    <span>Checking Facts</span>
                </div>
                <div class="step" id="step4">
                    <div class="step-icon">4</div>
                    <span>Finalizing Results</span>
                </div>
            </div>
        </div>

        <div id="result"></div>
    </div>

    <script>
        let currentStep = 0;
        let progressInterval;
        let stepInterval;

        async function checkConsistency() {
            const documentText = document.getElementById('document').value.trim();
            const summaryText = document.getElementById('summary').value.trim();
            
            if (!documentText || !summaryText) {
                alert('Please provide both document and summary.');
                return;
            }

            const resultDiv = document.getElementById('result');
            const loadingDiv = document.getElementById('loading');
            const checkBtn = document.getElementById('check-btn');
            const progressFill = document.querySelector('.progress-fill');
            
            // Reset previous results
            resultDiv.style.display = 'none';
            resultDiv.innerHTML = '';
            
            // Show loading animation
            loadingDiv.style.display = 'block';
            checkBtn.disabled = true;
            checkBtn.textContent = 'Analyzing...';
            
            // Reset progress and steps
            currentStep = 0;
            progressFill.style.width = '0%';
            document.querySelectorAll('.step').forEach(step => {
                step.classList.remove('active', 'completed');
            });
            
            // Start progress animation
            let progress = 0;
            progressInterval = setInterval(() => {
                progress += Math.random() * 8 + 2;
                if (progress > 90) progress = 90;
                progressFill.style.width = progress + '%';
            }, 150);
            
            // Start step animation
            stepInterval = setInterval(() => {
                if (currentStep < 4) {
                    // Complete current step
                    if (currentStep > 0) {
                        const prevStep = document.getElementById(`step${currentStep}`);
                        prevStep.classList.remove('active');
                        prevStep.classList.add('completed');
                    }
                    
                    // Activate next step
                    currentStep++;
                    const nextStep = document.getElementById(`step${currentStep}`);
                    nextStep.classList.add('active');
                }
            }, 800);

            try {
                const response = await fetch('/check_consistency', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        document: documentText,
                        summary: summaryText,
                    }),
                });

                const result = await response.json();
                
                // Complete progress
                clearInterval(progressInterval);
                clearInterval(stepInterval);
                progressFill.style.width = '100%';
                
                // Complete all steps
                document.querySelectorAll('.step').forEach(step => {
                    step.classList.remove('active');
                    step.classList.add('completed');
                });
                
                // Show results after a brief delay
                setTimeout(() => {
                    loadingDiv.style.display = 'none';
                    
                    if (response.ok) {
                        const verdictColor = result.verdict === 'consistent' ? '#4CAF50' : '#f44336';
                        const verdictIcon = result.verdict === 'consistent' ? '✅' : '❌';
                        
                        resultDiv.innerHTML = `
                            <h3 style="color: ${verdictColor};">
                                ${verdictIcon} Verdict: ${result.verdict.toUpperCase()}
                            </h3>
                            <p><b>Analysis:</b></p>
                            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 10px; font-family: 'Courier New', monospace; line-height: 1.6;">
                                ${result.reasoning.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\\n/g, '<br>')}
                            </div>
                        `;
                    } else {
                        resultDiv.innerHTML = `
                            <p style="color: #f44336;">
                                <b>❌ Error:</b> ${result.error}
                            </p>
                        `;
                    }
                    
                    resultDiv.style.display = 'block';
                    checkBtn.disabled = false;
                    checkBtn.textContent = 'Check Consistency';
                }, 500);

            } catch (error) {
                clearInterval(progressInterval);
                clearInterval(stepInterval);
                loadingDiv.style.display = 'none';
                
                resultDiv.innerHTML = `
                    <p style="color: #f44336;">
                        <b>❌ Error:</b> ${error.message}
                    </p>
                `;
                resultDiv.style.display = 'block';
                checkBtn.disabled = false;
                checkBtn.textContent = 'Check Consistency';
            }
        }
        document.getElementById('check-btn').addEventListener('click', checkConsistency);
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
    client = OpenAI(api_key="sk-62d5e4cd33674b4aa3f54c320f254169", base_url="https://api.deepseek.com")
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

def extract_ranking_order(response_text: str, num_summaries: int) -> list:
    """
    Extract the ranking order from the LLM response.
    Returns a list of indices in the order they should appear (best to worst).
    """
    # Look for numbered lists in the response
    lines = response_text.split('\n')
    ranking_order = []
    
    # Try to find explicit ranking patterns
    for line in lines:
        # Look for patterns like "1. Summary 3", "1) Summary 2", etc.
        match = re.search(r'^(\d+)[\.\)]\s*Summary\s*(\d+)', line.strip(), re.IGNORECASE)
        if match:
            summary_num = int(match.group(2)) - 1  # Convert to 0-based index
            if 0 <= summary_num < num_summaries and summary_num not in ranking_order:
                ranking_order.append(summary_num)
    
    # If we couldn't extract the full ranking, try alternative patterns
    if len(ranking_order) != num_summaries:
        ranking_order = []
        # Look for any mention of summary numbers in order
        for line in lines:
            numbers = re.findall(r'\b(\d+)\b', line)
            for num_str in numbers:
                num = int(num_str) - 1
                if 0 <= num < num_summaries and num not in ranking_order:
                    ranking_order.append(num)
    
    # If still incomplete, fill with remaining indices
    if len(ranking_order) < num_summaries:
        for i in range(num_summaries):
            if i not in ranking_order:
                ranking_order.append(i)
    
    return ranking_order[:num_summaries]

def rank_summaries_with_llm(document: str, summaries: list) -> dict:
    """
    Enhanced function to rank summaries with better prompting and parsing.
    """
    api_key = "sk-62d5e4cd33674b4aa3f54c320f254169"
    if not api_key:
        return {
            "success": False,
            "error": "API Error: DEEPSEEK_API_KEY environment variable not set."
        }
    
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    # Create a numbered list of summaries for the prompt
    summaries_text = "\n".join([f"Summary {i+1}:\n{s}\n" for i, s in enumerate(summaries)])
    
    prompt = f"""You are an expert evaluator of text summaries. Your task is to rank the provided summaries from BEST to WORST based on these criteria:

1. **Factual Accuracy**: Are all facts in the summary correct according to the document?
2. **Completeness**: Does the summary capture the main points and important details?
3. **Consistency**: Are there any contradictions or unsupported claims?
4. **Clarity**: Is the summary well-written and easy to understand?

<Document>
{document}
</Document>

<Summaries to Rank>
{summaries_text}
</Summaries to Rank>

Please provide:
1. A detailed analysis of each summary's strengths and weaknesses
2. Your reasoning for the ranking
3. The final ranking as a clear numbered list (1 = best, {len(summaries)} = worst)

Format your final ranking exactly like this:
**Final Ranking:**
1. Summary [number]
2. Summary [number]
3. Summary [number]
(etc.)

Answer:"""

    try:
        response = client.chat.completions.create(
            model='deepseek-chat',
            messages=[
                {"role": "system", "content": "You are an expert text analyst who evaluates summaries for accuracy, completeness, and quality. Always provide clear, structured feedback with explicit rankings."},
                {"role": "user", "content": prompt}
            ],
            stream=False,
            temperature=0.1  # Low temperature for more consistent rankings
        )
        
        response_text = response.choices[0].message.content
        ranking_order = extract_ranking_order(response_text, len(summaries))
        
        return {
            "success": True,
            "ranking_order": ranking_order,
            "explanation": response_text,
            "raw_response": response_text
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"API Error: {str(e)}"
        }

# Route to serve the main HTML page
@app.route('/')
def index():
    return render_template_string(CONSISTENCY_PAGE_HTML, active_page='consistency')

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
@app.route('/rank')
def ranking_page():
    return render_template_string(RANKING_PAGE_HTML, active_page='ranking')
@app.route('/rank_summaries', methods=['POST'])
def rank_summaries_endpoint():
    data = request.get_json()
    if not data or not data.get('document') or not data.get('summaries'):
        return jsonify({'error': 'Document and summaries are required.'}), 400
    
    summaries = data['summaries']
    if len(summaries) < 2:
        return jsonify({'error': 'At least 2 summaries are required for ranking.'}), 400
    
    result = rank_summaries_with_llm(data['document'], summaries)
    
    if result['success']:
        return jsonify({
            'success': True,
            'ranking_order': result['ranking_order'],
            'explanation': result['explanation']
        })
    else:
        return jsonify({'error': result['error']}), 500
if __name__ == '__main__':
    app.run(debug=True, port=5000)
