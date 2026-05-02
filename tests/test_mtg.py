import pytest

from bot.cogs.Mtg import Mtg


@pytest.mark.asyncio
async def test_fetch_card_returns_first_card(bot, mock_http_session):
    card_payload = {
        "cards": [
            {
                "name": "Lightning Bolt",
                "manaCost": "{R}",
                "type": "Instant",
                "text": "Lightning Bolt deals 3 damage to any target.",
            }
        ]
    }
    mock_http_session.mocked.get(
        "https://api.magicthegathering.io/v1/cards?name=Lightning+Bolt",
        payload=card_payload,
    )

    card = await Mtg(bot).fetch_card("Lightning Bolt")

    assert card is not None
    assert card["name"] == "Lightning Bolt"
    assert card["manaCost"] == "{R}"
