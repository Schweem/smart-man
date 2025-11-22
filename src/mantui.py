from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, Label, Static

from openai import OpenAI
from helpers import get_active_model
from fetcher import async_fetch

class ManTUI(App):
    """
    Main TUI class, contains the css styling, layout, 
    and core structure for the application
    """

    TITLE = "Smart-man"
    SUB_TITLE = "RTFM."

    CSS = """
    /* Layout */
    #sidebar { width: 20%; dock: left; border-right: solid $accent; background: $panel; }
    #chat-container { width: 100%; height: 100%; padding: 1; margin: 1; border: solid $accent; }
    
    /* Styling */
    .sidebar-header { text-align: center; background: $accent; color: black; padding: 1; width: 100%; }
    .status-box { background: $surface; border: solid $accent; margin: 1; padding: 1; color: $text-muted; }
    .active-manual { color: $accent; text-style: bold; }

    #cmd_input:focus{ border: purple }
    #chat_input:focus{ border: purple }
    #mdl_active{ color: purple }
    
    Input { margin: 1 0; }
    
    /* Chat Bubbles */
    ChatBubble { padding: 1; margin-bottom: 1; background: $surface; border: wide transparent; }
    .user-msg { border-left: wide $accent; background: $surface-lighten-1; }
    .ai-msg { border-left: wide purple; }
    """

    BINDINGS = [("q", "quit", "Quit")]

    current_manual_name = None
    current_manual_text = None

    def compose(self) -> ComposeResult:
        """
        We use compose in textual for building layouts
        In this case we are placing and preparing all the 
        major components.
        """

        yield Header()
        with Horizontal():
            # side bar, left
            with Vertical(id="sidebar"):
                yield Label("Control Panel", classes="sidebar-header")
                yield Input(placeholder="Load Command (e.g. tar)", id="cmd_input")
                
                # chat info, left center
                with Vertical(classes="status-box"):
                    yield Label("Active Manual:", classes="label")
                    yield Label("None", id="lbl_active", classes="active-manual")
                    yield Label("", id="lbl_status")
                    yield Label("Active Model:", classes="model-label")
                    try:
                        yield Label("Loading...", id="mdl_active", classes="active-manual")
                    except Exception as e:
                        yield Label(e, id="mdl_active", classes="active-manual")

            # chat window, right 
            with VerticalScroll(id="chat-container"):
                pass
                
        yield Input(placeholder="Ask about the manual...", id="chat_input", classes="dock-bottom")
        yield Footer()

    def on_mount(self):
        """
        On mount is when a widget is added. 
        Here we immediatley call for model name
        """

        self.check_model_status()
        self.screen.styles.border = ("outer", "orange")

    @work(thread=True)
    def check_model_status(self):
        """
        Here we are making a threaded call to update the label. 
        This is more performant than calling the function 
        at runtime. 
        """

        status = get_active_model()
        self.call_from_thread(self.query_one("#mdl_active", Label).update, status)

    async def on_input_submitted(self, event: Input.Submitted):
        """
        input handled, deals with either new chats or man page changes
        """

        val = event.value
        event.input.value = ""

        # load new man page if we submitted one
        if event.input.id == "cmd_input":
            await self.load_manual(val)
        
        # otherwise treat it as a chat message
        elif event.input.id == "chat_input":
            if not self.current_manual_text:
                self.notify("Please load a manual first!", severity="error")
                return
            
            # user message to chat
            await self.add_message("You", val, "user-msg")
            
            # stream llm response to use
            self.stream_ai_response(val, self.current_manual_text)

    async def load_manual(self, command_name):
        """
        Switch loaded man page in context, updates sidebar
        """

        lbl_status = self.query_one("#lbl_status", Label)
        lbl_active = self.query_one("#lbl_active", Label)
        
        lbl_status.update(f"Fetching {command_name}...")
        
        text = await async_fetch(command_name)
        
        if text:
            # update labels and display 
            self.current_manual_name = command_name
            self.current_manual_text = text[:15000] #15k is my current stopping point for context reasons
            
            lbl_active.update(command_name)
            lbl_status.update("Loaded & Ready.\n")
            
            # clear chat when loading new manual
            container = self.query_one("#chat-container")
            await container.remove_children() 
            
            self.notify(f"Manual for {command_name} loaded.")
        else:
            lbl_status.update("Error.")
            self.notify(f"Could not find manual for {command_name}", severity="error")

    async def add_message(self, speaker, text, css_class):
        """
        Controls look and behavior of chat window as messages are added
        """

        container = self.query_one("#chat-container", VerticalScroll)
        widget = ChatBubble(f"{speaker}: {text}", classes=css_class)

        await container.mount(widget)
        widget.scroll_visible()

        return widget

    @work(exclusive=True, thread=True)
    def stream_ai_response(self, question, context_text):
        """
        Main loop, takes input, updates ui, and generate response
        """

        def create_bubble():
            container = self.query_one("#chat-container", VerticalScroll)
            widget = ChatBubble("Model is thinking...", classes="ai-msg")
            container.mount(widget)
            widget.scroll_visible()
            return widget
            
        ai_widget = self.call_from_thread(create_bubble)

        client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
        
        system_prompt = (
            f"You are an expert on CLI tools. Answer briefly based ONLY on the text below.\n"
            f"MANUAL: {context_text}"
        )

        try:
            stream = client.chat.completions.create(
                model="local-model", 
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': question}, 
                ],
                stream=True, # otherwise it just sits 
                temperature=0.1,
            )

            full_response = ""
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content # build response with stream
                    
                    self.call_from_thread(ai_widget.update, f"[bold purple]AI:[/bold purple] {full_response}")

        except Exception as e:
            self.call_from_thread(ai_widget.update, f"[red]Error:[/red] {str(e)}")

class ChatBubble(Static):
    """A widget to hold a single message (User or AI)."""
    pass

if __name__ == "__main__":
    app = ManTUI()
    app.run()