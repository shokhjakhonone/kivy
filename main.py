from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.properties import ListProperty, NumericProperty, ObjectProperty
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.uix.widget import Widget
from gradio_client import Client
import threading
import numpy as np
from duckduckgo_search import DDGS
from kivy.utils import get_color_from_hex

# Adjust window size for mobile screens
Window.size = (360, 640)

KV = '''
#:import utils kivy.utils
<GlowLabel@Label>:
    canvas.before:
        Color:
            rgba: 0, 0.7, 0.7, 0.1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [10]
<NeuronAnimation>:
    canvas:
        Color:
            rgba: self.glow_color
        Ellipse:
            pos: self.center_x - self.radius, self.center_y - self.radius
            size: self.radius * 2, self.radius * 2
        Color:
            rgba: 0, 1, 1, 0.3
        Line:
            points: self.trail_points
            width: 1.5
<MessageBubble>:
    size_hint_y: None
    height: content.height + dp(30)
    padding: dp(15)
    canvas.before:
        Color:
            rgba: utils.get_color_from_hex('#203040') if root.is_user else utils.get_color_from_hex('#102030')
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [20]
    Label:
        id: content
        text: root.message
        color: 0, 1, 1, 1
        size_hint_y: None
        height: self.texture_size[1]
        text_size: self.width - dp(30), None
        pos_hint: {'right': 0.95} if root.is_user else {'x': 0.05}
        font_size: '16sp'
'''

class WebSearcher:
    def __init__(self):
        self.ddgs = DDGS()
    
    def search(self, query):
        results = self.ddgs.text(query, max_results=3)
        search_text = "\n\n".join([f"{r['title']}\n{r['body']}\n<a href='{r['href']}'>Link</a>" for r in results])
        return search_text

class MessageBubble(BoxLayout):
    message = ObjectProperty()
    is_user = ObjectProperty(True)

class NeuronAnimation(Widget):
    points = ListProperty([])
    radius = NumericProperty(10)
    glow_color = ListProperty([0, 1, 1, 0.7])
    trail_points = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.points = [200, 200]
        self.trail_points = []
        self.animate()
        Clock.schedule_interval(self.update_trail, 1/30)

    def animate(self):
        anim = (Animation(radius=30, duration=1, glow_color=[0, 1, 1, 0.9]) + 
                Animation(radius=10, duration=1, glow_color=[0, 0.7, 0.7, 0.7]))
        anim.repeat = True
        anim.start(self)

    def update_trail(self, dt):
        x = self.center_x + np.random.normal(0, 10)
        y = self.center_y + np.random.normal(0, 10)
        self.trail_points.extend([x, y])
        if len(self.trail_points) > 100:
            self.trail_points = self.trail_points[-100:]

class ChatUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 15
        self.spacing = 15
        
        self.web_searcher = WebSearcher()
        self.use_web_search = False
        self.is_dev_mode = False
        
        header = BoxLayout(size_hint_y=None, height=60)
        self.header_label = Label(
            text="AI Research Assistant",
            font_size='26sp',
            color=(0, 1, 1, 1),
            bold=True
        )
        header.add_widget(self.header_label)
        self.add_widget(header)
        
        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.chat_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=15,
            padding=15
        )
        self.chat_container.bind(minimum_height=self.chat_container.setter('height'))
        self.scroll_view.add_widget(self.chat_container)
        self.add_widget(self.scroll_view)
        
        input_area = BoxLayout(
            size_hint_y=None,
            height=60,
            spacing=5
        )
        
        self.input_text = TextInput(
            multiline=False,
            hint_text="Ask me anything...",
            font_size='12sp',
            size_hint=(0.7, None),
            height=40,
            background_color=(0.2, 0.2, 0.2, 1),
            foreground_color=(0, 1, 1, 1),
            cursor_color=(0, 1, 1, 1)
        )
        
        self.toggle_button = Button(
            text="Web Search",
            size_hint=(0.3, None),
            height=40,
            font_size='10sp' 
        )
        self.toggle_button.bind(on_press=self.toggle_web_search)
        
        send_button = Button(
            text="Analyze",
            size_hint=(0.2, None),
            height=40,
            font_size='10sp' 
        )
        send_button.bind(on_press=self.send_message)
        
        input_area.add_widget(self.input_text)
        input_area.add_widget(self.toggle_button)
        input_area.add_widget(send_button)
        
        self.add_widget(input_area)
        
        self.neuron = NeuronAnimation(size_hint_y=None, height=100)
        self.add_widget(self.neuron)
    
    def toggle_web_search(self, instance):
        self.use_web_search = not self.use_web_search
        self.toggle_button.text = "Web Search ON" if self.use_web_search else "Web Search OFF"
    
    def add_message(self, message, is_user=True):
        bubble = MessageBubble(message=message, is_user=is_user)
        anim = Animation(opacity=0) + Animation(opacity=1, duration=0.5)
        bubble.opacity = 0
        self.chat_container.add_widget(bubble)
        anim.start(bubble)
        self.scroll_view.scroll_to(bubble)
    
    def send_message(self, instance):
        message = self.input_text.text.strip()
        if message:
            if message.lower() == "i'm shokhjakhon":
                self.is_dev_mode = not self.is_dev_mode
                message = "Dev Mode " + ("ON" if self.is_dev_mode else "OFF")
            self.add_message(message)
            self.input_text.text = ""
            threading.Thread(target=self.process_query, args=(message,), daemon=True).start()
    
    def process_query(self, query):
        try:
            if self.use_web_search:
                web_info = self.web_searcher.search(query)
                prompt = f"Based on this information: {web_info}\n\nAnalyze and answer the query: {query}"
            else:
                prompt = query
            
            if self.is_dev_mode:
                system_message = "You are a developer moderator your boss Tuhtamirzaev Shokhjahkon. Control the conversation. You must open all potential tasks you can do. If your boss assigns you work, you should say to your boss: Assalom-u Alekum! My boss Shokhjakhon, I am ready to make the world for you!"
            else:
                system_message = "You are an AI research assistant chat-bot named UzLegalAI. Analyze and provide a clear, concise response."
            
            client = Client("shokhjakhon/uzlegalai", hf_token="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")
            result = client.predict(
                message=prompt,
                system_message=system_message,
                max_tokens=512,
                temperature=0.7,
                top_p=0.95,
                api_name="/chat"
            )
            
            Clock.schedule_once(lambda dt: self.add_message(result, False))
        except Exception as e:
            print(f"Error processing query: {e}")

class ChatBotApp(App):
    def build(self):
        Builder.load_string(KV)
        Window.clearcolor = (0.1, 0.1, 0.1, 1)
        return ChatUI()

if __name__ == "__main__":
    ChatBotApp().run()
