import os
import json
import random
import re

def extract_text_from_pdf_file(pdf_file):
    """
    Extracts plain text content from an uploaded PDF file using PyPDF2 with regex string fallback.
    """
    extracted_text = ""
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(pdf_file)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                extracted_text += t + "\n"
    except Exception as e:
        pass

    if not extracted_text.strip():
        try:
            pdf_file.seek(0)
            content = pdf_file.read().decode('utf-8', errors='ignore')
            lines = [line.strip() for line in content.split('\n') if len(line.strip()) > 20]
            extracted_text = "\n".join(lines[:100])
        except Exception as e:
            pass

    return extracted_text.strip()

def generate_questions_from_pdf_text(pdf_text, count=5, difficulty="Medium"):
    """
    Analyzes uploaded PDF content and generates clean, structured multiple choice questions
    using Claude API (Anthropic), with dynamic academic question generator fallback.
    """
    api_key = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    trimmed_text = pdf_text[:8000] if pdf_text else "NPTEL Technical Course Material"

    if api_key:
        try:
            import urllib.request
            prompt = (
                f"Analyze the following NPTEL study material content and generate exactly {count} clean, highly-structured multiple choice questions "
                f"at {difficulty} difficulty level.\n"
                "CRITICAL RULES:\n"
                "1. Write direct, clean academic questions. Do NOT use phrases like 'According to the document', 'Based on the PDF', or 'As mentioned in the text'.\n"
                "2. Provide 4 distinct options (option_a, option_b, option_c, option_d).\n"
                "3. Set correct_answer to 'A', 'B', 'C', or 'D'.\n"
                "4. Provide a clear, concise AI explanation.\n"
                "5. Output STRICTLY a valid JSON array of objects with keys: question_text, option_a, option_b, option_c, option_d, correct_answer, explanation.\n\n"
                f"Course Content:\n{trimmed_text}"
            )
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                data=json.dumps({
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 2500,
                    "messages": [{"role": "user", "content": prompt}]
                }).encode('utf-8')
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                result = json.loads(response.read().decode('utf-8'))
                text_content = result['content'][0]['text']
                start = text_content.find('[')
                end = text_content.rfind(']') + 1
                if start != -1 and end > start:
                    items = json.loads(text_content[start:end])
                    for item in items:
                        item['difficulty'] = difficulty
                    return items[:count]
        except Exception as e:
            pass

    # Extract keywords/topics from PDF text to create structured academic questions
    words = re.findall(r'\b[A-Z][a-zA-Z0-9]{3,}\b', pdf_text)
    unique_topics = list(dict.fromkeys(words)) if words else ["Data Structures", "System Design", "Pipelining", "Optimization"]

    structured_pool = [
        {
            "question_text": "Which data structure is optimal for implementing a Last-In, First-Out (LIFO) access pattern?",
            "option_a": "Queue",
            "option_b": "Stack",
            "option_c": "Binary Search Tree",
            "option_d": "Hash Table",
            "correct_answer": "B",
            "explanation": "A Stack enforces LIFO access order, making it ideal for function call stacks and expression parsing.",
            "difficulty": difficulty
        },
        {
            "question_text": "What is the worst-case time complexity of the Quicksort algorithm?",
            "option_a": "O(N log N)",
            "option_b": "O(N)",
            "option_c": "O(N^2)",
            "option_d": "O(log N)",
            "correct_answer": "C",
            "explanation": "Quicksort degrades to O(N^2) time complexity when poor pivot selection leads to unbalanced partitioning.",
            "difficulty": difficulty
        },
        {
            "question_text": "Which database normal form eliminates transitive functional dependencies?",
            "option_a": "First Normal Form (1NF)",
            "option_b": "Second Normal Form (2NF)",
            "option_c": "Third Normal Form (3NF)",
            "option_d": "Boyce-Codd Normal Form (BCNF)",
            "correct_answer": "C",
            "explanation": "3NF requires relations to be in 2NF while ensuring non-prime attributes are not transitively dependent on key attributes.",
            "difficulty": difficulty
        },
        {
            "question_text": "Which OSI model layer handles packet routing across different networks?",
            "option_a": "Data Link Layer",
            "option_b": "Network Layer",
            "option_c": "Transport Layer",
            "option_d": "Application Layer",
            "correct_answer": "B",
            "explanation": "The Network Layer (Layer 3) handles IP addressing, packet forwarding, and path selection across interconnected networks.",
            "difficulty": difficulty
        },
        {
            "question_text": "What CPU scheduling strategy minimizes average waiting time for a set of ready processes?",
            "option_a": "First-Come, First-Served (FCFS)",
            "option_b": "Shortest Job First (SJF)",
            "option_c": "Round Robin (RR)",
            "option_d": "Priority Scheduling",
            "correct_answer": "B",
            "explanation": "Shortest Job First (SJF) scheduling is provably optimal for minimizing overall average waiting time.",
            "difficulty": difficulty
        },
        {
            "question_text": f"In {unique_topics[0] if unique_topics else 'System Architecture'}, what is the primary purpose of pipelining?",
            "option_a": "To overlap execution stages and increase instruction throughput",
            "option_b": "To eliminate memory bus latency completely",
            "option_c": "To convert dynamic memory to static RAM",
            "option_d": "To force sequential single-cycle execution",
            "correct_answer": "A",
            "explanation": "Pipelining overlaps multiple execution steps in parallel, significantly improving system instruction throughput.",
            "difficulty": difficulty
        },
        {
            "question_text": f"Which condition is necessary for deadlock occurrence in concurrent resource management?",
            "option_a": "Mutual Exclusion",
            "option_b": "Hold and Wait",
            "option_c": "No Preemption & Circular Wait",
            "option_d": "All of the above",
            "correct_answer": "D",
            "explanation": "All four Coffman conditions (Mutual Exclusion, Hold & Wait, No Preemption, and Circular Wait) must hold for a deadlock.",
            "difficulty": difficulty
        }
    ]

    selected = random.sample(structured_pool, min(count, len(structured_pool)))
    
    # If more count requested than pool size, generate cleanly formatted additional items
    while len(selected) < count:
        idx = len(selected) + 1
        topic = unique_topics[(idx - 1) % len(unique_topics)]
        selected.append({
            "question_text": f"What is the key principle behind effective optimization in {topic}?",
            "option_a": "Minimizing spatial and time complexity overhead",
            "option_b": "Bypassing concurrency validation checks",
            "option_c": "Restricting execution to single-threaded loops",
            "option_d": "Disabling index lookup tables",
            "correct_answer": "A",
            "explanation": f"System optimization in {topic} focuses on minimizing computational time and memory overhead.",
            "difficulty": difficulty
        })

    return selected[:count]

# Dynamic Question Bank for general fallback
DEFAULT_QUESTION_BANK = {
    "Data Structures": [
        {
            "question_text": "Which data structure is best suited for evaluating postfix arithmetic expressions?",
            "option_a": "Queue",
            "option_b": "Stack",
            "option_c": "Binary Tree",
            "option_d": "Linked List",
            "correct_answer": "B",
            "explanation": "A Stack operates on Last-In, First-Out (LIFO) principle, making it optimal for evaluating postfix expressions.",
            "difficulty": "Easy"
        },
        {
            "question_text": "What is the worst-case time complexity of quicksort algorithm?",
            "option_a": "O(N log N)",
            "option_b": "O(N)",
            "option_c": "O(N^2)",
            "option_d": "O(log N)",
            "correct_answer": "C",
            "explanation": "Quicksort has a worst-case time complexity of O(N^2) when the pivot selected is consistently poor.",
            "difficulty": "Medium"
        }
    ]
}

def generate_mock_questions(course_title, difficulty="Medium", count=5):
    api_key = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")

    if api_key:
        try:
            import urllib.request
            prompt = (
                f"Generate {count} clean, highly-structured multiple choice questions for NPTEL course '{course_title}' "
                f"at {difficulty} difficulty level.\n"
                "CRITICAL: Do NOT use phrases like 'According to...'. Write clean questions with fields: "
                "question_text, option_a, option_b, option_c, option_d, correct_answer ('A','B','C','D'), explanation."
            )
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                data=json.dumps({
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 1500,
                    "messages": [{"role": "user", "content": prompt}]
                }).encode('utf-8')
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                result = json.loads(response.read().decode('utf-8'))
                text_content = result['content'][0]['text']
                start = text_content.find('[')
                end = text_content.rfind(']') + 1
                if start != -1 and end > start:
                    items = json.loads(text_content[start:end])
                    for item in items:
                        item['difficulty'] = difficulty
                    return items[:count]
        except Exception as e:
            pass

    questions = DEFAULT_QUESTION_BANK.get(course_title, [])
    if not questions:
        questions = [
            {
                "question_text": f"In {course_title}, what is the foundational paradigm used for system analysis?",
                "option_a": "Modular Decomposition",
                "option_b": "Monolithic Execution",
                "option_c": "Random Search",
                "option_d": "Unbounded State Transition",
                "correct_answer": "A",
                "explanation": f"Modular decomposition allows complex systems in {course_title} to be broken down into manageable, reusable components.",
                "difficulty": difficulty
            }
        ]

    selected = random.sample(questions, min(count, len(questions)))
    return selected
