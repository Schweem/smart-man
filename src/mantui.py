from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, Label, Static, Collapsible, ListView, ListItem, Markdown, TabPane, TabbedContent, Input

from openai import OpenAI
from helpers import get_active_model, fetch_models, is_embedding
from fetcher import async_fetch

class ManTUI(App):
    """
    Main TUI class, contains the css styling, layout, 
    and core structure for the application
    """

    TITLE = "Smart-man"
    SUB_TITLE = "RTFM."

    api_endpoint = "http://localhost:1234/v1"
    api_key = "lm-studio"

    selected_model = "local-model" # temp placeholder, falls back to loaded model in LMStudio

    CSS = """
    /* Layout */
    #sidebar { width: 20%; dock: left; border-right: solid $accent; background: $panel; }
    #chat-container { width: 100%; height: 100%; padding: 1; margin: 1; border: solid $accent; background: $boost }
    
    /* Styling */
    .sidebar-header { text-align: center; background: $accent; color: black; padding: 1; width: 100%; }
    .status-box { background: $surface; border: solid $accent; margin: 1; padding: 1; color: $text-muted; }
    .active-manual { color: $accent; text-style: bold; }

    #cmd_input:focus{ border: purple }
    #chat_input:focus{ border: purple }
    #mdl_active{ color: purple }

    ListView { margin: 0 1; }
    TabbedContent { margin: 1 1; }
    Input { margin: 1 0; }
    
    /* Chat Bubbles */
    ChatBubble { padding: 1; margin-bottom: 1; background: $surface; border: wide transparent; }
    .user-msg { border-left: wide $accent; background: $surface-lighten-1; }
    .ai-msg { border-left: wide purple; }
    """

    BINDINGS = [("q", "quit", "Quit")]

    current_manual_name = None
    current_manual_text = None

    def on_mount(self):
        """
        On mount is when a widget is added. 
        Here we immediatley call for model name
        """

        self.check_model_status()
        self.screen.styles.border = ("outer", "orange")
        
        model_list = self.query_one("#model-list", ListView)
        # loop through models and add availible ones to the list
        try:
            for model in fetch_models():
                if is_embedding(model.id):
                    continue
                item = ListItem(Label(model.id))
                item.target_id = model.id # using a custom id field due to naming issues with textual id

                model_list.append(item)
                #model_list.append(ListItem(Label(model.id)))

        except Exception as e:
            model_list.append(ListItem(Label("Error connecting to endpoint. \nCheck connection.")))
            print(f"Error fetching models: {e}")

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
                with TabbedContent(initial="model"):
                    with TabPane("Model", id="model"):
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
                            
                            with Collapsible(title="Models", classes="mdl-select"):
                                yield ListView(id="model-list")

                    with TabPane("API", id="api"):
                        yield Label("OpenAPI Endpoint:")
                        yield Input(placeholder="http://localhost:1234/v1", id="endpoint")
                        yield Label("API Key:")
                        yield Input(placeholder="lm-studio", id="apikey")

            # chat window, right
            with VerticalScroll(id="chat-container"):
                pass
                
        yield Input(placeholder="Ask about the manual...", id="chat_input", classes="dock-bottom")
        yield Footer()

    @work(thread=True)
    def check_model_status(self):
        """
        Here we are making a threaded call to update the label. 
        This is more performant than calling the function 
        at runtime. 
        """

        status = get_active_model(self.api_endpoint, self.api_key)
        self.call_from_thread(self.query_one("#mdl_active", Label).update, status)

    def on_list_view_selected(self, event: ListView.Selected):
        """
        even handler for selection in list view
        handles model change
        """
        
        new_model_id = event.item.target_id # grab selected model
        
        self.selected_model = new_model_id # set it
        
        # update labels and text
        self.query_one("#mdl_active", Label).update(new_model_id)
        self.notify(f"Model switched to {new_model_id}")

    async def on_input_submitted(self, event: Input.Submitted):
        """
        input handled, deals with either new chats or man page changes
        """

        try:
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

            # check for api endpoint submission
            elif event.input.id == "endpoint":
                self.api_endpoint = event.value
                self.update_models()

            # same for api key
            elif event.input.id == "apikey":
                self.api_key = event.value

        except Exception as e:
            print(f"Something went wrong: {e}")

    def update_models(self):
        """
        Helper function to refresh the model list when we change api keys
        """
        try:
            model_list = self.query_one("#model-list", ListView) # grab it
            model_list.clear() # clear it

            for model in fetch_models(self.api_endpoint, self.api_key): # query it
                if is_embedding(model.id):
                    continue
                item = ListItem(Label(model.id))
                item.target_id = model.id # using a custom id field due to naming issues with textual id

                model_list.append(item)
                
        except Exception as e:
            print(f"Error: {e}")

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

        client = OpenAI(base_url=self.api_endpoint, api_key=self.api_key)
        
        system_prompt = (
            f"You are an expert on CLI tools. Answer briefly based ONLY on the text below.\n"
            f"MANUAL: {context_text}"
            f"ALWAYS use /no_think"
        )

        try:
            stream = client.chat.completions.create(
                model=self.selected_model, 
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': question}, 
                ],
                stream=True, # otherwise it just sits and waits 
                temperature=0.1, # low temp for consitent responses
            )

            full_response = "" # start empty             
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content # build response with stream
                    
                    self.call_from_thread(ai_widget.update, f"**Smart-man:** {full_response}")

        except Exception as e:
            self.call_from_thread(ai_widget.update, f"**Error:** {str(e)}")

class ChatBubble(Markdown):
    """A widget to hold a single message (User or AI)."""
    pass

if __name__ == "__main__":
    app = ManTUI()
    app.run()