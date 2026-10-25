from r6cast.detect import parse_killfeed


def test_parses_killer_and_victim():
    text = "Soren.R6  @> Enemy_Ash\nTeamMate99 =- Bandit_Main\nnoise"
    assert parse_killfeed(text) == [("Soren.R6", "Enemy_Ash"), ("TeamMate99", "Bandit_Main")]
