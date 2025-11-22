from fetcher import async_fetch

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog, Static
from textual.containers import Container
from textual import work

class MainTui(App):
    CSS = """
    Input {
        dock: top;
        margin: 1 0;
    }

    #results {
        width: 100%;
        height: 100%;
        border: solid green;
        background: $surface;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Enter a shell command...")
        yield RichLog(id="results", highlight=True, markup=False)
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted):
        command = event.value
        log = self.query_one('#results', RichLog)

        event.input.value = ""

        log.clear()
        log.write(f"Grabbing man page for: {command}.\n")

        result = await async_fetch(command)

        if result:
            log.write(result)
        else:
            log.write(f"[red]Error retrieving man page.")

if __name__ == "__main__":
    app = MainTui()
    app.run()