import os
import re
import gradio as gr
import modelscope_studio.components.antd as antd
import modelscope_studio.components.base as ms
import modelscope_studio.components.pro as pro
from groq import Groq

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set")

client = Groq(api_key=GROQ_API_KEY)

# Set default model
DEFAULT_MODEL = "llama-3.3-70b-versatile"

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

# React Imports
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

class GradioEvents:

    @staticmethod
    def generate_code(input_value, system_prompt_input_value, state_value, selected_model):
        """Generate code with improved error handling and state management"""
        
        def get_generated_files(text):
            """Extract code blocks from response"""
            patterns = {
                'html': r'```html\n(.+?)\n```',
                'jsx': r'```jsx\n(.+?)\n```',
                'tsx': r'```tsx\n(.+?)\n```',
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
        
        if not input_value or input_value.strip() == '':
            yield {
                output: gr.update(value="⚠️ Please enter a description of what you want to create."),
                output_loading: gr.update(spinning=False),
                state_tab: gr.update(active_key="empty"),
                suggestions_container: gr.update(visible=False),
                download_btn: gr.update(disabled=True)
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
            "content": system_prompt_input_value or SYSTEM_PROMPT
        }] + state_value["history"]

        messages.append({'role': "user", 'content': input_value.strip()})

        max_tokens = 8192
        for model in AVAILABLE_MODELS:
            if model["value"] == selected_model:
                max_tokens = model["max_tokens"]
                break

        try:
            completion = client.chat.completions.create(
                model=selected_model,
                messages=messages,
                temperature=1,
                max_completion_tokens=max_tokens,
                top_p=1,
                stream=True,
                stop=None
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
                    state_value["history"] = messages + [{
                        'role': "assistant",
                        'content': response
                    }]
                    
                    generated_files = get_generated_files(response)
                    react_code = generated_files.get("index.tsx") or generated_files.get("index.jsx")
                    html_code = generated_files.get("index.html")
                    
                    code_to_download = react_code or html_code
                    
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
            
            if "authentication" in error_message.lower() or "api key" in error_message.lower():
                friendly_message = "🔐 **Authentication Error**: Invalid API key. Please check your Groq API key."
            elif "rate limit" in error_message.lower():
                friendly_message = "⏱️ **Rate Limit**: Too many requests. Please wait a moment and try again."
            elif "timeout" in error_message.lower():
                friendly_message = "⏰ **Timeout Error**: The request took too long. Please try again with a simpler prompt."
            elif "model" in error_message.lower():
                friendly_message = f"🤖 **Model Error**: Issue with model '{selected_model}'. Try selecting a different model."
            else:
                friendly_message = f"❌ **Error ({error_type})**: {error_message}"
            
            yield {
                output: gr.update(value=friendly_message),
                output_loading: gr.update(spinning=False),
                state_tab: gr.update(active_key="loading"),
                suggestions_container: gr.update(visible=False),
                download_btn: gr.update(disabled=True)
            }

    @staticmethod
    def update_model_info(selected_model):
        """Update model info text when model is changed"""
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
        """Validate input before submission"""
        if not input_value or len(input_value.strip()) < 10:
            gr.Warning("Please provide a more detailed description (at least 10 characters).")
            return False
        return True

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
"""

theme = gr.themes.Default()

with gr.Blocks(title="Groq AI WebDev Coder", theme=theme, css=css) as demo:
    # Global State
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
                                    "https://i.ibb.co/fYRyJNq/Screenshot-from-2025-11-04-08-53-02.png",
                                    width=200,
                                    height=200,
                                    preview=False)
                                antd.Typography.Title(
                                    "Groq AI WebDev",
                                    level=1,
                                    elem_style=dict(fontSize=24))
                                
                            # Model Selection Card - FIXED: Set default value
                            with antd.Card(
                                title="🤖 Select AI Model",
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
                                # Get default model description
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
                            
                            submit_btn = antd.Button("🚀 Generate Code",
                                                     type="primary",
                                                     block=True,
                                                     size="large",
                                                     elem_id="submit-btn")

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

                            # Examples
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

                    # Right Column
                    with antd.Col(span=24, md=16):
                        with antd.Card(
                                title="✨ Output Preview",
                                elem_style=dict(height="100%",
                                                display="flex",
                                                flexDirection="column"),
                                styles=dict(body=dict(height=0, flex=1)),
                                elem_id="output-container"):
                            # FIXED: Single download button in card extra
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
                            
                            # Hidden component for download content
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
                        
                        # AI Suggestions Panel
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

                    # Modals and Drawers
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
    

    model_selector.change(
        fn=GradioEvents.update_model_info,
        inputs=[model_selector],
        outputs=[selected_model_info]
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
