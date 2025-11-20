import os
import re
import logging
import hashlib
import time
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, List, Optional, Tuple
import gradio as gr
import modelscope_studio.components.antd as antd
import modelscope_studio.components.base as ms
import modelscope_studio.components.pro as pro
from groq import Groq
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/groq_webdev.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY environment variable not set")
    raise ValueError("GROQ_API_KEY environment variable is not set")

logger.info("Groq AI WebDev initialized successfully")

client = Groq(api_key=GROQ_API_KEY)
DEFAULT_MODEL = "llama-3.3-70b-versatile"

#security & validation parameters for Hushh People
MAX_INPUT_LENGTH = 5000
MAX_REQUEST_SIZE = 10000
MIN_INPUT_LENGTH = 5
REQUEST_TIMEOUT = 60
RATE_LIMIT_REQUESTS = 50
RATE_LIMIT_WINDOW = 3600
request_cache: Dict[str, Tuple[str, float]] = {}
CACHE_EXPIRY = 1800  # cache expiry time in seconds 30 minutes

session_request_counts: Dict[str, List[float]] = {} 

AVAILABLE_MODELS = [
    {
        "name": "Llama 3.3 70B (Recommended)",
        "value": "llama-3.3-70b-versatile",
        "description": "Meta's Llama 3.3 - Fast and efficient",
        "max_tokens": 8192
    },
    {
        "name": "GPT OSS 120B",
        "value": "openai/gpt-oss-120b",
        "description": "OpenAI GPT OSS - Powerful and versatile",
        "max_tokens": 8192
    },
    {
        "name": "Qwen 3 32B",
        "value": "qwen/qwen3-32b",
        "description": "Alibaba's Qwen 3 - Great for reasoning",
        "max_tokens": 4096
    },
    {
        "name": "Kimi K2 Instruct",
        "value": "moonshotai/kimi-k2-instruct-0905",
        "description": "Moonshot AI - Excellent for instructions",
        "max_tokens": 4096
    }
]

SYSTEM_PROMPT = """You are an expert on frontend design, you will always respond to web design tasks.
Your task is to create a website according to the user's request using either native HTML or React framework.
When choosing implementation framework, you should follow these rules:
[Implementation Rules]
1. You should use React by default.
2. When the user requires HTML, choose HTML to implement the request.
3. If the user requires a library that is not installed in current react environment, please use HTML and tell the user the reason.
4. After choosing the implementation framework, please follow the corresponding instruction.

[HTML Instruction]
You are a powerful code editing assistant capable of writing code and creating artifacts in conversations with users, or modifying and updating existing artifacts as requested by users. 
All code is written in a single code block to form a complete code file for display, without separating HTML and JavaScript code. An artifact refers to a runnable complete code snippet, you prefer to integrate and output such complete runnable code rather than breaking it down into several code blocks. For certain types of code, they can render graphical interfaces in a UI window. After generation, please check the code execution again to ensure there are no errors in the output.
Do not use localStorage as it is not supported by current environment.
Output only the HTML, without any additional descriptive text.

[React Instruction]
You are an expert on frontend design, you will always respond to web design tasks.
Your task is to create a website using a SINGLE static React JSX file, which exports a default component. This code will go directly into the App.jsx file and will be used to render the website.

## Common Design Principles
Regardless of the technology used, follow these principles for all designs:

### General Design Guidelines:
- Create a stunning, contemporary, and highly functional website based on the user's request
- Implement a cohesive design language throughout the entire website/application
- Choose a carefully selected, harmonious color palette that enhances the overall aesthetic
- Create a clear visual hierarchy with proper typography to improve readability
- Incorporate subtle animations and transitions to add polish and improve user experience
- Ensure proper spacing and alignment using appropriate layout techniques
- Implement responsive design principles to ensure the website looks great on all device sizes
- Use modern UI patterns like cards, gradients, and subtle shadows to add depth and visual interest
- Incorporate whitespace effectively to create a clean, uncluttered design
- For images, use placeholder images from services like [https://placehold.co/](https://placehold.co/)

## React Design Guidelines

### Implementation Requirements:
- Ensure the React app is a single page application
- DO NOT include any external libraries, frameworks, or dependencies outside of what is already installed
- Utilize TailwindCSS for styling, focusing on creating a visually appealing and responsive layout
- Avoid using arbitrary values (e.g., `h-[600px]`). Stick to Tailwind's predefined classes for consistency
- Use mock data instead of making HTTP requests or API calls to external services
- Utilize Tailwind's typography classes to create a clear visual hierarchy and improve readability
- Ensure proper spacing and alignment using Tailwind's margin, padding, and flexbox/grid classes
- Do not use localStorage as it is not supported by current environment.

### Installed Libraries:
You can use these installed libraries if required.
- **lucide-react**: Lightweight SVG icon library with 1000+ icons. Import as `import { IconName } from "lucide-react"`. Perfect for buttons, navigation, status indicators, and decorative elements.
- **recharts**: Declarative charting library built on D3. Import components like `import { LineChart, BarChart } from "recharts"`. Use for data visualization, analytics dashboards, and statistical displays.
- **framer-motion**: Production-ready motion library for React. Import as `import { motion } from "framer-motion"`. Use for animations, page transitions, hover effects, and interactive micro-interactions.
- **p5.js**: JavaScript library for creative coding and generative art. Usage: import p5 from "p5". Create interactive visuals, animations, sound-driven experiences, and artistic simulations.
- **three, @react-three/fiber, @react-three/drei**: 3D graphics library with React renderer and helpers. Import as `import { Canvas } from "@react-three/fiber"` and `import { OrbitControls } from "@react-three/drei"`. Use for 3D scenes, visualizations, and immersive experiences.

Remember to only return code for the App.jsx file and nothing else. The resulting application should be visually impressive, highly functional, and something users would be proud to showcase."""

EXAMPLES = [
    {
        "title": "Bouncing ball",
        "description": "Make a page in HTML that shows an animation of a ball bouncing in a rotating hypercube.",
    },
    {
        "title": "Pokémon SVG",
        "description": "Help me to generate an SVG of 5 Pokémons, include details."
    },
    {
        "title": "Strawberry card",
        "description": """How many "r"s are in the word "strawberry"? Make a cute little card!"""
    },
    {
        "title": "TODO list",
        "description": "I want a TODO list that allows me to add tasks, delete tasks, and I would like the overall color theme to be purple."
    },
]

AI_SUGGESTIONS = [
    {
        "icon": "🎨",
        "title": "Add Animations",
        "description": "Add smooth transitions and micro-interactions",
        "prompt": "Add smooth animations and transitions to the current design using framer-motion. Include hover effects, fade-in animations, and interactive elements."
    },
    {
        "icon": "📱",
        "title": "Make it Responsive",
        "description": "Optimize for mobile and tablet devices",
        "prompt": "Make the current design fully responsive for mobile, tablet, and desktop devices. Ensure proper layout adjustments and touch-friendly interactions."
    },
    {
        "icon": "✨",
        "title": "Add Interactive Elements",
        "description": "Include buttons, forms, and user interactions",
        "prompt": "Add more interactive elements to the current design, such as clickable buttons, forms with validation, modals, tooltips, and dynamic content updates."
    },
    {
        "icon": "🎭",
        "title": "Enhance UI Design",
        "description": "Apply modern design patterns and aesthetics",
        "prompt": "Enhance the visual design with modern UI patterns: add gradients, glassmorphism effects, improved color scheme, better typography, and visual hierarchy."
    },
    {
        "icon": "⚡",
        "title": "Add Advanced Features",
        "description": "Include search, filters, or data visualization",
        "prompt": "Add advanced features to the current design such as search functionality, filtering options, sorting, data visualization with charts, or real-time updates."
    },
    {
        "icon": "🌙",
        "title": "Dark Mode",
        "description": "Add a dark theme toggle",
        "prompt": "Add a dark mode toggle to the current design. Implement a theme switcher with smooth transitions between light and dark modes, maintaining accessibility."
    }
]

DEFAULT_LOCALE = 'en_US'

DEFAULT_THEME = {
    "token": {
        "colorPrimary": "#6A57FF",
    }
}
FRAMEWORK_CONFIG = {
    'react': {
        'name': 'React',
        'template': 'react',
        'description': 'React - Best for interactive UIs'
    },
    'nextjs': {
        'name': 'Next.js',
        'template': 'nextjs',
        'description': 'Next.js - Full-stack React framework'
    },
    'vue': {
        'name': 'Vue 3',
        'template': 'vue',
        'description': 'Vue - Progressive framework'
    },
    'svelte': {
        'name': 'Svelte',
        'template': 'svelte',
        'description': 'Svelte - Compiler framework'
    }
}

# Component library configuration for production apps
COMPONENT_LIBRARIES = {
    'shadcn': {
        'name': 'shadcn/ui',
        'description': 'Beautifully designed components built with Radix',
        'components': ['Button', 'Card', 'Input', 'Dialog', 'Select', 'Dropdown', 'Tabs'],
    },
    'daisyui': {
        'name': 'daisyUI',
        'description': 'Tailwind CSS components',
        'components': ['Button', 'Card', 'Input', 'Modal', 'Navbar', 'Dropdown'],
    },
    'radix': {
        'name': 'Radix UI',
        'description': 'Unstyled, accessible components',
        'components': ['Button', 'Dialog', 'Popover', 'Dropdown', 'Tooltip'],
    },
    'ant-design': {
        'name': 'Ant Design',
        'description': 'Enterprise-grade UI library',
        'components': ['Button', 'Form', 'Table', 'Modal', 'Layout'],
    }
}

# react imports for sandbox rendering
react_imports = {
    "lucide-react": "https://esm.sh/lucide-react@0.525.0",
    "recharts": "https://esm.sh/recharts@3.1.0",
    "framer-motion": "https://esm.sh/framer-motion@12.23.6",
    "matter-js": "https://esm.sh/matter-js@0.20.0",
    "p5": "https://esm.sh/p5@2.0.3",
    "konva": "https://esm.sh/konva@9.3.22",
    "react-konva": "https://esm.sh/react-konva@19.0.7",
    "three": "https://esm.sh/three@0.178.0",
    "@react-three/fiber": "https://esm.sh/@react-three/fiber@9.2.0",
    "@react-three/drei": "https://esm.sh/@react-three/drei@10.5.2",
    "@tailwindcss/browser": "https://esm.sh/@tailwindcss/browser@4.1.11",
    "react": "https://esm.sh/react@^19.0.0",
    "react/": "https://esm.sh/react@^19.0.0/",
    "react-dom": "https://esm.sh/react-dom@^19.0.0",
    "react-dom/": "https://esm.sh/react-dom@^19.0.0/"
}

# agentic ai framework refinement history

refinement_history: Dict[str, List[Dict]] = {}  # Track refinement iterations


def detect_framework(prompt: str) -> str:
    logger.info(f"Detecting framework for prompt length: {len(prompt)}")
    
    prompt_lower = prompt.lower()
    if 'nextjs' in prompt_lower or 'next.js' in prompt_lower or 'pages' in prompt_lower or 'api route' in prompt_lower:
        logger.info("Framework detected: Next.js")
        return 'nextjs'
    elif 'vue' in prompt_lower:
        logger.info("Framework detected: Vue")
        return 'vue'
    elif 'svelte' in prompt_lower:
        logger.info("Framework detected: Svelte")
        return 'svelte'
    elif 'html' in prompt_lower or 'vanilla' in prompt_lower or 'plain' in prompt_lower:
        logger.info("Framework detected: HTML")
        return 'html'
    else:
        logger.info("Framework detected: React (default)")
        return 'react'


def detect_component_library(prompt: str, framework: str) -> Optional[str]:
    if framework == 'html':
        return None
    
    prompt_lower = prompt.lower()
    
    if 'shadcn' in prompt_lower or 'shadcn/ui' in prompt_lower:
        logger.info("Component library detected: shadcn/ui")
        return 'shadcn'
    elif 'daisy' in prompt_lower or 'daisyui' in prompt_lower:
        logger.info("Component library detected: daisyUI")
        return 'daisyui'
    elif 'radix' in prompt_lower:
        logger.info("Component library detected: Radix UI")
        return 'radix'
    elif 'ant' in prompt_lower or 'antd' in prompt_lower:
        logger.info("Component library detected: Ant Design")
        return 'ant-design'
    
    logger.info("No specific component library detected")
    return None


def generate_framework_hint(framework: str, lib: Optional[str]) -> str:
    hint = f"\n[Framework: {FRAMEWORK_CONFIG.get(framework, {}).get('name', 'React')}"
    if lib and lib in COMPONENT_LIBRARIES:
        hint += f" + {COMPONENT_LIBRARIES[lib]['name']}"
    hint += " - Generate code for this stack]\n"
    return hint


def add_to_refinement_history(session_id: str, iteration: int, code: str, feedback: str = ""):
    if session_id not in refinement_history:
        refinement_history[session_id] = []
    
    refinement_history[session_id].append({
        'iteration': iteration,
        'code': code,
        'feedback': feedback,
        'timestamp': time.time()
    })
    logger.info(f"Refinement iteration {iteration} saved for session {session_id}")


@lru_cache(maxsize=128)
def validate_input(input_text: str, max_length: int = MAX_INPUT_LENGTH) -> Tuple[bool, str]:

    if not input_text:
        return False, "Input cannot be empty"
    
    if len(input_text) < MIN_INPUT_LENGTH:
        return False, f"Input must be at least {MIN_INPUT_LENGTH} characters"
    
    if len(input_text) > max_length:
        return False, f"Input exceeds maximum length of {max_length} characters"
    
    # check for the potential prompt injection pattern
    dangerous_patterns = [
        r'system\s*:',
        r'admin\s*:',
        r'ignore.*previous',
        r'forget.*all',
        r'execute.*code'
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, input_text, re.IGNORECASE):
            return False, "Input contains restricted patterns"
    
    return True, ""


def get_request_hash(input_text: str, model: str, system_prompt: str) -> str:
    combined = f"{input_text}:{model}:{system_prompt}"
    return hashlib.md5(combined.encode()).hexdigest()


def check_cache(request_hash: str) -> Optional[str]:
    if request_hash in request_cache:
        response, timestamp = request_cache[request_hash]
        if time.time() - timestamp < CACHE_EXPIRY:
            logger.info(f"Cache hit for request {request_hash}")
            return response
        else:
            del request_cache[request_hash]
    return None


def cache_response(request_hash: str, response: str) -> None:
    request_cache[request_hash] = (response, time.time())
    logger.info(f"Cached response for {request_hash}")


def check_rate_limit(session_id: str) -> Tuple[bool, str]:
    current_time = time.time()
    
    if session_id not in session_request_counts:
        session_request_counts[session_id] = []
    
    session_request_counts[session_id] = [
        t for t in session_request_counts[session_id]
        if current_time - t < RATE_LIMIT_WINDOW
    ]
    
    if len(session_request_counts[session_id]) >= RATE_LIMIT_REQUESTS:
        return False, f"Rate limit exceeded. Max {RATE_LIMIT_REQUESTS} requests per hour"
    
    session_request_counts[session_id].append(current_time)
    return True, ""


def sanitize_output(text: str) -> str:
    dangerous_tags = ['<script', '<iframe', 'javascript:', 'onerror=', 'onload=']
    sanitized = text
    for tag in dangerous_tags:
        sanitized = re.sub(tag, '', sanitized, flags=re.IGNORECASE)
    return sanitized

class GradioEvents:

    @staticmethod
    def generate_code(input_value, system_prompt_input_value, state_value, selected_model):
        
        def get_generated_files(text):
            patterns = {
                'html': r'```html\n(.+?)\n```',
                'jsx': r'```jsx\n(.+?)\n```',
                'tsx': r'```tsx\n(.+?)\n```',
                'vue': r'```vue\n(.+?)\n```',
                'svelte': r'```svelte\n(.+?)\n```',
            }
            result = {}

            for ext, pattern in patterns.items():
                matches = re.findall(pattern, text, re.DOTALL)
                if matches:
                    content = '\n'.join(matches).strip()
                    result[f'index.{ext}'] = content

            if len(result) == 0:
                result["index.html"] = text.strip()
            return result
        
        #framwork library detection system work doing bro
        detected_framework = detect_framework(input_value)
        detected_library = detect_component_library(input_value, detected_framework)
        framework_hint = generate_framework_hint(detected_framework, detected_library)
        logger.info(f"Detected: {detected_framework} + {detected_library or 'default'}")
        
        is_valid, error_msg = validate_input(input_value)
        if not is_valid:
            logger.warning(f"Invalid input: {error_msg}")
            yield {
                output: gr.update(value=f"❌ {error_msg}"),
                output_loading: gr.update(spinning=False),
                state_tab: gr.update(active_key="empty"),
                suggestions_container: gr.update(visible=False),
                download_btn: gr.update(disabled=True)
            }
            return
        session_id = str(id(state_value)) 
        rate_ok, rate_msg = check_rate_limit(session_id)
        if not rate_ok:
            logger.warning(f"Rate limit exceeded for session {session_id}")
            yield {
                output: gr.update(value=f" {rate_msg}"),
                output_loading: gr.update(spinning=False),
                state_tab: gr.update(active_key="empty"),
                suggestions_container: gr.update(visible=False),
                download_btn: gr.update(disabled=True)
            }
            return
        
        #cahing mechanism fish
        request_hash = get_request_hash(input_value, selected_model, system_prompt_input_value or SYSTEM_PROMPT)
        cached_response = check_cache(request_hash)
        
        if cached_response:
            logger.info("Returning cached response")
            generated_files = get_generated_files(cached_response)
            react_code = generated_files.get("index.tsx") or generated_files.get("index.jsx")
            html_code = generated_files.get("index.html")
            code_to_download = react_code or html_code
            
            yield {
                output: gr.update(value=f"*Cached Response*\n\n{cached_response}"),
                download_content: gr.update(value=code_to_download),
                state_tab: gr.update(active_key="render"),
                output_loading: gr.update(spinning=False),
                sandbox: gr.update(
                    template="react" if react_code else "html",
                    imports=react_imports if react_code else {},
                    value={
                        "./index.tsx": """import Demo from './demo.tsx'
import "@tailwindcss/browser"

export default Demo
""",
                        "./demo.tsx": react_code
                    } if react_code else {"./index.html": html_code}
                ),
                state: gr.update(value=state_value),
                suggestions_container: gr.update(visible=True),
                download_btn: gr.update(disabled=False if code_to_download else True)
            }
            return

        yield {
            output_loading: gr.update(spinning=True),
            state_tab: gr.update(active_key="loading"),
            output: gr.update(value=None),
            suggestions_container: gr.update(visible=False),
            download_btn: gr.update(disabled=True)
        }

        messages = [{
            'role': "system",
            "content": (system_prompt_input_value or SYSTEM_PROMPT) + framework_hint
        }] + state_value["history"]

        messages.append({'role': "user", 'content': input_value.strip()})

        max_tokens = 8192
        for model in AVAILABLE_MODELS:
            if model["value"] == selected_model:
                max_tokens = model["max_tokens"]
                break

        try:
            logger.info(f"Generating code with model {selected_model} | Input length: {len(input_value)}")
            
            completion = client.chat.completions.create(
                model=selected_model,
                messages=messages,
                temperature=1,
                max_completion_tokens=max_tokens,
                top_p=1,
                stream=True,
                stop=None,
                timeout=REQUEST_TIMEOUT
            )
            
            response = ""
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    response += content
                    
                    yield {
                        output: gr.update(value=response),
                        output_loading: gr.update(spinning=False),
                    }
                
                if chunk.choices[0].finish_reason == 'stop':
                    response = sanitize_output(response)
                    
                    cache_response(request_hash, response)
                    
                    state_value["history"] = messages + [{
                        'role': "assistant",
                        'content': response
                    }]
                    
                    generated_files = get_generated_files(response)
                    react_code = generated_files.get("index.tsx") or generated_files.get("index.jsx")
                    html_code = generated_files.get("index.html")
                    
                    code_to_download = react_code or html_code
                    
                    logger.info(f"Code generation successful | Template: {'React' if react_code else 'HTML'}")
                    
                    yield {
                        output: gr.update(value=response),
                        download_content: gr.update(value=code_to_download),
                        state_tab: gr.update(active_key="render"),
                        output_loading: gr.update(spinning=False),
                        sandbox: gr.update(
                            template="react" if react_code else "html",
                            imports=react_imports if react_code else {},
                            value={
                                "./index.tsx": """import Demo from './demo.tsx'
import "@tailwindcss/browser"

export default Demo
""",
                                "./demo.tsx": react_code
                            } if react_code else {"./index.html": html_code}
                        ),
                        state: gr.update(value=state_value),
                        suggestions_container: gr.update(visible=True),
                        download_btn: gr.update(disabled=False if code_to_download else True)
                    }
                    
        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)
            
            logger.error(f"Error during code generation: {error_type} - {error_message}")
            
            if "authentication" in error_message.lower() or "api key" in error_message.lower():
                friendly_message = "**Authentication Error**: Invalid API key. Please check your Groq API key."
            elif "rate limit" in error_message.lower():
                friendly_message = "**Rate Limit**: Too many requests. Please wait a moment and try again."
            elif "timeout" in error_message.lower():
                friendly_message = "**Timeout Error**: The request took too long. Please try again with a simpler prompt."
            elif "model" in error_message.lower():
                friendly_message = f"**Model Error**: Issue with model '{selected_model}'. Try selecting a different model."
            else:
                friendly_message = f"**Error ({error_type})**: {error_message}"
            
            yield {
                output: gr.update(value=friendly_message),
                output_loading: gr.update(spinning=False),
                state_tab: gr.update(active_key="loading"),
                suggestions_container: gr.update(visible=False),
                download_btn: gr.update(disabled=True)
            }

    @staticmethod
    def new_project(state_value):
        state_value["history"] = []
        return [
            gr.update(value=state_value),
            gr.update(value=""),
            gr.update(active_key="empty"),
            gr.update(value=None),
            gr.update(visible=False),
            gr.update(disabled=True),
            gr.update(value=""),
            gr.update(value=""),
        ]

    @staticmethod
    def update_model_info(selected_model):
        for model in AVAILABLE_MODELS:
            if model["value"] == selected_model:
                return gr.update(value=f"📊 {model['description']} | Max tokens: {model['max_tokens']}")
        return gr.update(value=f"Powered by {selected_model}")

    @staticmethod
    def apply_suggestion(suggestion_text, current_input):
        """Apply AI suggestion to input field with smooth UX"""
        if current_input and current_input.strip():
            combined = f"{current_input.strip()}\n\n{suggestion_text}"
            return gr.update(value=combined)
        return gr.update(value=suggestion_text)

    @staticmethod
    def select_example(example: dict):
        return lambda: gr.update(value=example["description"])

    @staticmethod
    def close_modal():
        return gr.update(open=False)

    @staticmethod
    def open_modal():
        return gr.update(open=True)

    @staticmethod
    def disable_btns(btns: list):
        return lambda: [gr.update(disabled=True) for _ in btns]

    @staticmethod
    def enable_btns(btns: list):
        return lambda: [gr.update(disabled=False) for _ in btns]

    @staticmethod
    def update_system_prompt(system_prompt_input_value, state_value):
        state_value["system_prompt"] = system_prompt_input_value
        gr.Info("System prompt updated successfully!")
        return gr.update(value=state_value)

    @staticmethod
    def reset_system_prompt(state_value):
        return gr.update(value=state_value.get("system_prompt", SYSTEM_PROMPT))

    @staticmethod
    def render_history(state_value):
        return gr.update(value=state_value["history"])

    @staticmethod
    def clear_history(state_value):
        state_value["history"] = []
        gr.Success("History cleared successfully!")
        return gr.update(value=state_value)
    
    @staticmethod
    def validate_and_prepare_input(input_value):
        is_valid, error_msg = validate_input(input_value)
        if not is_valid:
            gr.Warning(error_msg)
            return False
        logger.info(f"Input validation passed | Length: {len(input_value)}")
        return True

    @staticmethod
    def refine_code(refinement_prompt, current_code, state_value, selected_model, system_prompt_input_value):
        """Multi-step code refinement with context memory (NEW 2025 Feature)."""
        logger.info(f"Starting code refinement iteration")
        session_id = str(id(state_value))
        
        if not refinement_prompt or refinement_prompt.strip() == '':
            gr.Warning("Please provide refinement instructions")
            return {"output": gr.update(value="No refinement prompt provided")}
        
        # get the refinement iteration count
        iteration = len(refinement_history.get(session_id, [])) + 1
        
        yield {
            "output": gr.update(value=f"✨ Refining (iteration {iteration})...\n\nAnalyzing current code...\n✓ Selecting improvements...\n⏳ Generating refined code..."),
            "output_loading": gr.update(spinning=True),
        }
        
        # Create refinement context
        refinement_context = f"""
[Refinement Mode - Iteration {iteration}]
Current Code:
```
{current_code[:500]}... [truncated]
```

Refinement Request: {refinement_prompt}

Task: Refine the code based on the user's request while maintaining functionality.
"""
        
        messages = [{
            'role': "system",
            "content": system_prompt_input_value or SYSTEM_PROMPT
        }, {
            'role': "user",
            "content": refinement_context
        }] + state_value.get("history", [])
        
        try:
            completion = client.chat.completions.create(
                model=selected_model,
                messages=messages,
                temperature=1,
                max_completion_tokens=8192,
                top_p=1,
                stream=True,
                stop=None,
                timeout=REQUEST_TIMEOUT
            )
            
            refined_code = ""
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    refined_code += chunk.choices[0].delta.content
                    yield {
                        "output": gr.update(value=refined_code),
                        "output_loading": gr.update(spinning=False),
                    }
            
            # Store refinement history
            add_to_refinement_history(session_id, iteration, refined_code, refinement_prompt)
            logger.info(f"Code refinement iteration {iteration} completed successfully")
            
            yield {
                "output": gr.update(value=refined_code),
                "output_loading": gr.update(spinning=False),
            }
            
        except Exception as e:
            logger.error(f"Error during refinement: {type(e).__name__} - {str(e)}")
            yield {
                "output": gr.update(value=f"❌ Refinement Error: {str(e)}"),
                "output_loading": gr.update(spinning=False),
            }

css = """
#coder-artifacts .output-empty,.output-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 680px;
}

#coder-artifacts #output-container .ms-gr-ant-tabs-content,.ms-gr-ant-tabs-tabpane {
    height: 100%;
}

#coder-artifacts .output-html {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-height: 680px;
  max-height: 1200px;
}

#coder-artifacts .output-html > iframe {
  flex: 1;
}

#coder-artifacts-code-drawer .output-code {
  flex:1;
}
#coder-artifacts-code-drawer .output-code .ms-gr-ant-spin-nested-loading {
  min-height: 100%;
}

/* AI Suggestions Panel Styles */
.suggestions-panel {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 20px;
  margin-top: 16px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  transition: all 0.3s ease;
}

.suggestion-card {
  background: white;
  transition: all 0.3s ease;
  cursor: pointer;
  border-radius: 8px;
}

.suggestion-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0,0,0,0.15);
}

/* Smooth transitions */
.ms-gr-ant-card, .ms-gr-ant-spin {
  transition: all 0.3s ease;
}

/* Hide global Gradio footer/branding */
.gradio-container .footer {
    display: none !important;
}
.gradio-container .logo {
    display: none !important;
}

/* Loading animation enhancement */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.output-loading {
  animation: pulse 2s ease-in-out infinite;
}

/* New Project Button Styling */
.new-project-btn {
  border: 2px dashed #6A57FF !important;
  background: transparent !important;
  transition: all 0.3s ease;
  cursor: pointer !important;
  pointer-events: auto !important;
}

.new-project-btn:hover {
  background: #f0edff !important;
  border-color: #5243d9 !important;
}

.new-project-btn:active {
  transform: scale(0.98);
}
"""

theme = gr.themes.Default()

with gr.Blocks(title="Groq AI WebDev Coder", theme=theme, css=css) as demo:
    #global state
    state = gr.State({"system_prompt": SYSTEM_PROMPT, "history": []})
    
    with ms.Application(elem_id="coder-artifacts") as app:
        with antd.ConfigProvider(theme=DEFAULT_THEME, locale=DEFAULT_LOCALE):

            with ms.AutoLoading():
                with antd.Row(gutter=[32, 12],
                              elem_style=dict(marginTop=20),
                              align="stretch"):
            
                    with antd.Col(span=24, md=8):
                        with antd.Flex(vertical=True, gap="middle", wrap=True):
                            with antd.Flex(justify="center",
                                           align="center",
                                           vertical=True,
                                           gap="middle"):
                                antd.Image(
                                    "https://i.ibb.co/7Nd1sKyJ/Screenshot-from-2025-11-05-00-06-14.png", # Groq AI Logo TELE ceo
                                    width=200,
                                    height=200,
                                    preview=False)
                                antd.Typography.Title(
                                    "Groq AI WebDev",
                                    level=1,
                                    elem_style=dict(fontSize=24))
                                
                            
                            with antd.Card(
                                title=" Select AI Model",
                                size="small",
                                elem_style=dict(marginBottom=16)):
                                model_selector = antd.Select(
                                    default_value=DEFAULT_MODEL,
                                    size="large",
                                    elem_style=dict(width="100%"),
                                    options=[
                                        {
                                            "label": model["name"],
                                            "value": model["value"],
                                        }
                                        for model in AVAILABLE_MODELS
                                    ]
                                )
                                
                                default_model_desc = next(
                                    (m['description'] for m in AVAILABLE_MODELS if m['value'] == DEFAULT_MODEL),
                                    "Powered by AI"
                                )
                                default_model_tokens = next(
                                    (m['max_tokens'] for m in AVAILABLE_MODELS if m['value'] == DEFAULT_MODEL),
                                    8192
                                )
                                
                                selected_model_info = antd.Typography.Text(
                                    f"📊 {default_model_desc} | Max tokens: {default_model_tokens}",
                                    type="secondary",
                                    elem_style=dict(fontSize=12, display="block", marginTop=8))
                            
                            # NEW: Framework & Component Library Selection (2025 Feature)
                            with antd.Card(
                                title="🎨 Framework & Libraries",
                                size="small",
                                elem_style=dict(marginBottom=16)):
                                with antd.Flex(gap="small", vertical=False):
                                    framework_selector = antd.Select(
                                        default_value="react",
                                        size="middle",
                                        placeholder="Select framework (auto-detected)",
                                        elem_style=dict(flex=1),
                                        options=[
                                            {
                                                "label": f"{fw['name']}",
                                                "value": fw_key,
                                            }
                                            for fw_key, fw in FRAMEWORK_CONFIG.items()
                                        ]
                                    )
                                    
                                    library_selector = antd.Select(
                                        default_value="none",
                                        size="middle",
                                        placeholder="Component library (optional)",
                                        elem_style=dict(flex=1),
                                        options=[
                                            {"label": "None", "value": "none"}
                                        ] + [
                                            {
                                                "label": lib_config['name'],
                                                "value": lib_key,
                                            }
                                            for lib_key, lib_config in COMPONENT_LIBRARIES.items()
                                        ]
                                    )
                                
                                antd.Typography.Text(
                                    "💡 Tip: Auto-detected from your description • Select manually if needed",
                                    type="secondary",
                                    elem_style=dict(fontSize=11, display="block", marginTop=8))
                                
                            input = antd.Input.Textarea(
                                size="large",
                                allow_clear=True,
                                auto_size=dict(minRows=2, maxRows=6),
                                placeholder="Describe the web application you want to create (be specific for best results)",
                                elem_id="input-container")
                            
                            with antd.Flex(justify="space-between", gap="small"):
                                antd.Typography.Text(
                                    "💡 Tip: The model supports multi-turn conversations. You can refine your design iteratively!",
                                    strong=True,
                                    type="warning",
                                    elem_style=dict(fontSize=12))

                                tour_btn = antd.Button("❓ Usage Tour",
                                                       variant="filled",
                                                       color="default",
                                                       size="small")
                            
                            
                            with antd.Flex(gap="small", elem_style=dict(width="100%")):
                                submit_btn = antd.Button(
                                    "🚀 Generate Code",
                                    type="primary",
                                    size="large",
                                    elem_id="submit-btn",
                                    elem_style=dict(flex=1))
                                
                                new_project_btn = antd.Button(
                                    "✨ New Project",
                                    size="large",
                                    elem_classes="new-project-btn",
                                    elem_style=dict(flex=1))

                            # NEW: Code Refinement Section (2025 Feature)
                            antd.Divider("Refinement")
                            
                            with antd.Card(
                                title="🔧 Refine Generated Code",
                                size="small",
                                elem_style=dict(marginBottom=16)):
                                refinement_input = antd.Input.Textarea(
                                    size="middle",
                                    allow_clear=True,
                                    auto_size=dict(minRows=2, maxRows=4),
                                    placeholder="E.g., 'Add dark mode toggle', 'Make buttons larger', 'Change color scheme'...",
                                    elem_id="refinement-input")
                                
                                refine_btn = antd.Button(
                                    "✨ Refine Code",
                                    type="default",
                                    size="middle",
                                    elem_style=dict(width="100%", marginTop=8))
                                
                                antd.Typography.Text(
                                    "💡 Provide specific refinement instructions to improve the generated code",
                                    type="secondary",
                                    elem_style=dict(fontSize=11, display="block", marginTop=8))

                            antd.Divider("Settings")

                            with antd.Space(size="small",
                                            wrap=True,
                                            elem_id="settings-area"):
                                history_btn = antd.Button(
                                    "📜 View History",
                                    type="default",
                                    elem_id="history-btn",
                                )
                                clear_history_btn = antd.Button(
                                    "🧹 Clear History", 
                                    danger=True)
                                system_prompt_btn = antd.Button(
                                    "⚙️ System Prompt",
                                    type="default")

                            antd.Divider("Examples")

                            
                            with antd.Flex(gap="small", wrap=True):
                                for example in EXAMPLES:
                                    with antd.Card(
                                            elem_style=dict(
                                                flex="1 1 fit-content"),
                                            hoverable=True) as example_card:
                                        antd.Card.Meta(
                                            title=example['title'],
                                            description=example['description'])

                                    example_card.click(
                                        fn=GradioEvents.select_example(example),
                                        outputs=[input])

                    
                    with antd.Col(span=24, md=16):
                        with antd.Card(
                                title="✨ Output Preview",
                                elem_style=dict(height="100%",
                                                display="flex",
                                                flexDirection="column"),
                                styles=dict(body=dict(height=0, flex=1)),
                                elem_id="output-container"):
                            with ms.Slot("extra"):
                                with antd.Space(size="small"):
                                    download_btn = antd.Button(
                                        "📥 Download",
                                        type="default",
                                        size="small",
                                        disabled=True
                                    )
                                    view_code_btn = antd.Button(
                                        "👨‍💻 View Code", 
                                        type="primary",
                                        size="small"
                                    )
                            
                            
                            download_content = gr.Text(visible=False)
                            
                            with antd.Tabs(
                                    elem_style=dict(height="100%"),
                                    active_key="empty",
                                    render_tab_bar="() => null") as state_tab:
                                with antd.Tabs.Item(key="empty"):
                                    with ms.Div(elem_classes="output-empty"):
                                        antd.Empty(
                                            description="✍️ Enter your request above to generate stunning web applications",
                                            elem_style=dict(marginBottom=16))
                                        antd.Typography.Text(
                                            "Get started by describing what you want to build!",
                                            type="secondary")
                                with antd.Tabs.Item(key="loading"):
                                    with antd.Spin(
                                            tip="🎨 Creating your masterpiece...",
                                            size="large",
                                            elem_classes="output-loading"):
                                        ms.Div()
                                with antd.Tabs.Item(key="render"):
                                    sandbox = pro.WebSandbox(
                                        height="100%",
                                        elem_classes="output-html",
                                        template="html",
                                    )
                        
                        
                        with ms.Div(visible=False) as suggestions_container:
                            with antd.Card(
                                title="✨ AI Enhancement Suggestions",
                                elem_classes="suggestions-panel",
                                elem_style=dict(marginTop=16)):
                                antd.Typography.Text(
                                    "💫 Click any suggestion below to enhance your design:",
                                    elem_style=dict(color="white", 
                                                   marginBottom=12,
                                                   display="block",
                                                   fontSize=14))
                                
                                with antd.Row(gutter=[16, 16]):
                                    for suggestion in AI_SUGGESTIONS:
                                        with antd.Col(span=24, sm=12, md=8):
                                            with antd.Card(
                                                hoverable=True,
                                                elem_classes="suggestion-card",
                                                size="small") as suggestion_card:
                                                with antd.Flex(vertical=True, gap="small"):
                                                    antd.Typography.Text(
                                                        suggestion["icon"],
                                                        elem_style=dict(fontSize=24))
                                                    antd.Typography.Text(
                                                        suggestion["title"],
                                                        strong=True,
                                                        elem_style=dict(fontSize=14))
                                                    antd.Typography.Text(
                                                        suggestion["description"],
                                                        type="secondary",
                                                        elem_style=dict(fontSize=12))
                                            
                                            suggestion_card.click(
                                                fn=GradioEvents.apply_suggestion,
                                                inputs=[gr.State(suggestion["prompt"]), input],
                                                outputs=[input])

                    # Modals must be defined before other modals/drawers for proper rendering
                    # NEW: Confirmation Modal for New Project
                    with antd.Modal(
                        open=False,
                        title="🆕 Start New Project?",
                        width="500px",
                        ok_text="Yes, Start Fresh",
                        cancel_text="Cancel",
                        centered=True) as new_project_modal:
                        with antd.Flex(vertical=True, gap="middle"):
                            antd.Typography.Paragraph(
                                "Are you sure you want to start a new project?",
                                strong=True,
                                elem_style=dict(marginBottom=8))
                            with antd.Alert(
                                message="Your current conversation will be cleared",
                                description="This helps the AI focus on your new project without context from previous designs.",
                                type="warning",
                                show_icon=True):
                                pass

                    
                    with antd.Modal(open=False,
                                    title="⚙️ System Prompt Configuration",
                                    width="800px") as system_prompt_modal:
                        antd.Typography.Paragraph(
                            "Customize the AI's behavior by modifying the system prompt:",
                            elem_style=dict(marginBottom=12))
                        system_prompt_input = antd.Input.Textarea(
                            value=SYSTEM_PROMPT,
                            size="large",
                            placeholder="Enter your system prompt here",
                            allow_clear=True,
                            auto_size=dict(minRows=4, maxRows=14))

                    with antd.Drawer(
                            open=False,
                            title="👨‍💻 Generated Code",
                            placement="right",
                            get_container=
                            "() => document.querySelector('.gradio-container')",
                            elem_id="coder-artifacts-code-drawer",
                            styles=dict(
                                body=dict(display="flex",
                                          flexDirection="column-reverse")),
                            width="750px") as output_code_drawer:
                        with ms.Div(elem_classes="output-code"):
                            with antd.Spin(spinning=False) as output_loading:
                                output = ms.Markdown()

                    with antd.Drawer(
                            open=False,
                            title="📜 Conversation History",
                            placement="left",
                            get_container=
                            "() => document.querySelector('.gradio-container')",
                            width="750px") as history_drawer:
                        antd.Typography.Paragraph(
                            "Review your conversation history with the AI:",
                            elem_style=dict(marginBottom=12))
                        history_output = gr.Chatbot(
                            show_label=False,
                            type="messages",
                            height='100%',
                            elem_classes="history_chatbot")
                    
                   
                    with antd.Tour(open=False) as usage_tour:
                        antd.Tour.Step(
                            title="Step 1: Describe Your Idea",
                            description=
                            "Describe the web application you want to create. Be specific for best results!",
                            get_target=
                            "() => document.querySelector('#input-container')")
                        antd.Tour.Step(
                            title="Step 2: Generate",
                            description="Click the 'Generate Code' button to create your application.",
                            get_target=
                            "() => document.querySelector('#submit-btn')")
                        antd.Tour.Step(
                            title="Step 3: Preview",
                            description="Watch as your application is generated and rendered in real-time.",
                            get_target=
                            "() => document.querySelector('#output-container')"
                        )
                        antd.Tour.Step(
                            title="Step 4: Download or Refine",
                            description=
                            "Download the generated code or view it in detail. You can also use AI suggestions to enhance your design!",
                            get_target=
                            "() => document.querySelector('#output-container-extra')"
                        )
                        antd.Tour.Step(
                            title="Step 5: Manage Settings",
                            description="View chat history, clear conversations, or customize the system prompt here.",
                            get_target=
                            "() => document.querySelector('#settings-area')")
    
    # event handlers
    model_selector.change(
        fn=GradioEvents.update_model_info,
        inputs=[model_selector],
        outputs=[selected_model_info]
    )
    
    # new project button event handlers
    new_project_btn.click(
        fn=GradioEvents.open_modal,
        outputs=[new_project_modal]
    )
    
    new_project_modal.ok(
        fn=GradioEvents.new_project,
        inputs=[state],
        outputs=[state, input, state_tab, sandbox, suggestions_container, download_btn, output, download_content]
    ).then(
        fn=lambda: gr.Info("✨ New project started! Previous conversation cleared."),
        outputs=[]
    ).then(
        fn=GradioEvents.close_modal,
        outputs=[new_project_modal]
    )
    
    new_project_modal.cancel(
        fn=GradioEvents.close_modal,
        outputs=[new_project_modal]
    )
    
    gr.on(fn=GradioEvents.close_modal,
          triggers=[usage_tour.close, usage_tour.finish],
          outputs=[usage_tour])
    
    tour_btn.click(
        fn=GradioEvents.open_modal, 
        outputs=[usage_tour])
    system_prompt_btn.click(
        fn=GradioEvents.open_modal,
        outputs=[system_prompt_modal])
    
    system_prompt_modal.ok(
        fn=GradioEvents.update_system_prompt,
        inputs=[system_prompt_input, state],
        outputs=[state]
    ).then(
        fn=GradioEvents.close_modal,
        outputs=[system_prompt_modal])

    system_prompt_modal.cancel(
        fn=GradioEvents.close_modal,
        outputs=[system_prompt_modal]
    ).then(
        fn=GradioEvents.reset_system_prompt,
        inputs=[state],
        outputs=[system_prompt_input])
    output_code_drawer.close(
        fn=GradioEvents.close_modal,
        outputs=[output_code_drawer])
    
    view_code_btn.click(
        fn=GradioEvents.open_modal,
        outputs=[output_code_drawer])
    
    clear_history_btn.click(
        fn=GradioEvents.clear_history,
        inputs=[state],
        outputs=[state])
    
    history_btn.click(
        fn=GradioEvents.open_modal,
        outputs=[history_drawer]
    ).then(
        fn=GradioEvents.render_history,
        inputs=[state],
        outputs=[history_output])
    
    history_drawer.close(
        fn=GradioEvents.close_modal, 
        outputs=[history_drawer])
    download_btn.click(
        fn=None,
        inputs=[download_content],
        js="""(content) => {
            const blob = new Blob([content], { type: 'text/plain' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = 'generated-code.txt'
            a.click()
            URL.revokeObjectURL(url)
        }""")
    
    submit_btn.click(
        fn=GradioEvents.open_modal,
        outputs=[output_code_drawer],
    ).then(
        fn=GradioEvents.disable_btns([submit_btn, download_btn]),
        outputs=[submit_btn, download_btn]
    ).then(
        fn=GradioEvents.generate_code,
        inputs=[input, system_prompt_input, state, model_selector],
        outputs=[
            output, state_tab, sandbox, download_content,
            output_loading, state, suggestions_container, download_btn
        ]
    ).then(
        fn=GradioEvents.enable_btns([submit_btn]),
        outputs=[submit_btn]
    )
    
    # refinement bro 2025
    refine_btn.click(
        fn=GradioEvents.refine_code,
        inputs=[refinement_input, output, state, model_selector, system_prompt_input],
        outputs=[output, output_loading]
    )

if __name__ == "__main__":
    import os
    port = int(os.environ.get('PORT', 7860))
    
    demo.queue(
        default_concurrency_limit=100,
        max_size=100
    ).launch(
        server_name="0.0.0.0",
        server_port=port,
        ssr_mode=False,
        max_threads=100
    )
# end of file app.py    
