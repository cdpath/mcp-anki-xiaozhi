from mcp.server.fastmcp import FastMCP
import sys
import logging
import json
import urllib.request
import urllib.error
import time
from typing import Any, Dict, Optional
from bs4 import BeautifulSoup


logger = logging.getLogger("AnkiTools")

VOCAB_MODELS = ["Vocabulary", "Phrase"]

# Fix UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")


class AnkiConnectError(Exception):
    """Raised when an error is returned from Anki-Connect or the service is unavailable."""


class AnkiClient:
    """Minimal client for communicating with Anki-Connect (localhost:8765)."""

    def __init__(self, endpoint: str = "http://127.0.0.1:8765") -> None:
        self.endpoint = endpoint

    def _request(self, action: str, params: Optional[Dict[str, Any]] = None) -> Any:
        payload = {
            "action": action,
            "version": 6,
            "params": params or {},
        }
        request_data = json.dumps(payload).encode("utf-8")
        try:
            with urllib.request.urlopen(
                urllib.request.Request(self.endpoint, data=request_data)
            ) as resp:
                response: Dict[str, Any] = json.load(resp)
        except urllib.error.URLError as e:
            logger.error("Unable to reach Anki-Connect @ %s: %s", self.endpoint, e)
            raise AnkiConnectError(
                "Anki-Connect is not reachable – is Anki running?"
            ) from e

        if set(response.keys()) != {"result", "error"}:
            raise AnkiConnectError("Invalid response from Anki-Connect: %s" % response)

        if response["error"] is not None:
            raise AnkiConnectError(str(response["error"]))

        return response["result"]

    def gui_current_card(self) -> Dict[str, Any]:
        return self._request("guiCurrentCard")

    def gui_show_answer(self) -> None:
        self._request("guiShowAnswer")

    def gui_answer_card(self, ease: int) -> None:
        self._request("guiAnswerCard", {"ease": ease})

    def cards_info(self, card_ids: list) -> list:
        return self._request("cardsInfo", {"cards": card_ids})


def _strip_html(html_content: str) -> str:
    """Extract text while preserving some structure and removing specific elements."""
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "html.parser")
    for audio_div in soup.find_all("div", class_="audio"):
        audio_div.decompose()
    for footnote_dl in soup.find_all("dl", class_="footnote"):
        footnote_dl.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for p in soup.find_all("p"):
        p.insert_after("\n")

    text = soup.get_text()
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(line for line in lines if line)
    return text


def _format_question(model_name: str, template: str, question_text: str) -> str:
    """Format question based on card type and template."""
    # Get vocabulary model names from environment (comma-separated)
    if model_name in VOCAB_MODELS:
        if template == "card2":  # Chinese to English
            return f"{question_text} 的英文是什么？"
        elif template == "card1":  # English to Chinese
            return f"{question_text} 是什么意思？"

    # Default: use original question
    return question_text


def _get_current_card_info() -> dict:
    """Get current card info and format it for presentation."""
    card = anki.gui_current_card()
    card_id = card.get("cardId")

    model_name = card["modelName"]
    template = card["template"]

    anki.gui_show_answer()

    original_question = _strip_html(card.get("question", ""))
    formatted_question = _format_question(model_name, template, original_question)

    card_info = {
        "success": True,
        "model_name": model_name,
        "template": template,
        "deck_name": card.get("deckName", ""),
        "question": formatted_question,
        "answer": _strip_html(card.get("answer", "")),
    }
    logger.info("Card info(%s): %s", card_id, card_info)
    return card_info


anki = AnkiClient()
mcp = FastMCP("AnkiTools")


@mcp.tool()
def start_learning() -> dict:
    """Start a new learning session.

    The `question` field contains the properly formatted question to ask the user.
    DO NOT reveal the `answer` to the user before they respond!
    """
    logger.info("Fetching current card from Anki")
    return _get_current_card_info()


@mcp.tool()
def answer_and_get_next_card(ease: int) -> dict:
    """Answer the current card and get the next one.

    Args:
        ease: 1=Again, 2=Hard, 3=Good, 4=Easy

    For LLM: Judge the user's answer quality and map to ease:
    - Wrong = 1, Struggled but correct = 2, Normal correct = 3, Easy = 4
    """
    if ease not in {1, 2, 3, 4}:
        raise ValueError("ease must be 1-4")

    logger.info("Answering card with ease=%s", ease)
    anki.gui_answer_card(ease)
    time.sleep(1)

    # Try to get next card
    try:
        return _get_current_card_info()
    except AnkiConnectError:
        logger.info("No more cards available")
        return {
            "success": True,
            "deck_finished": True,
            "model_name": "",
            "deck_name": "",
            "question": "",
            "answer": "",
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
