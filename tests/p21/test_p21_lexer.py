# Copyright (c) 2020 Manfred Moitzi
# License: MIT License

import pytest
from steputils import p21


def test_lexer_skip_whitespace():
    l = p21.Lexer('  ;  \n  ;  ')
    assert list(l) == [';', ';']
    assert l.line_number == 2


def test_lexer_skip_comments():
    l = p21.Lexer('  ;\n/* xbyb();.,''""\\\\ */;')
    assert list(l) == [';', ';']
    assert l.line_number == 2


def test_lexer_skip_comments_nl():
    l = p21.Lexer('  ;\n/* xbyb();.,\n''""\\\\ */;')
    assert list(l) == [';', ';']
    assert l.line_number == 3


def test_lexer_missing_end_of_comment():
    l = p21.Lexer('  ;\n/* xbyb();.,\n''""\\\\ ;')
    with pytest.raises(p21.ParseError):
        list(l)
    assert l.line_number == 3


def test_lexer_invalid_keywords():
    # Lexer accepts invalid keywords if they are a valid reference -> parser check required
    assert list(p21.Lexer("#1=#100(100);")) == ['#1', '=', '#100', '(', 100, ')', ';']
    # But simple parameters like int, float, enum, binary and string will be detected
    # because of the invalid termination '('
    with pytest.raises(p21.ParseError):
        list(p21.Lexer("#1=100(100);"))


def test_lexer_simple_string():
    # String is always a parameter and therefor requires an following terminator ',' or ')'
    assert list(p21.Lexer("'ABC' ,")) == ['ABC', ',']
    # Characters like \n ot \t also terminate parameters
    assert type(list(p21.Lexer("'ABC'\t"))[0]) is str
    assert list(p21.Lexer("'ABC'\n")) == ['ABC']


def test_lexer_string_with_special_chars():
    r = list(p21.Lexer(r"'\X2\000F\X0\ ?*$',"))
    assert r == ['\u000f ?*$', ',']


def test_lexer_string_with_escaped_apostrophe():
    r = list(p21.Lexer("'Henry''s Pub',"))
    assert r == ["Henry's Pub", ',']


def test_lexer_string_with_enclosed_comments():
    r = list(p21.Lexer(r"'/* a comment */',"))
    assert r == ["/* a comment */", ',']


def test_lexer_string_across_lines():
    assert list(p21.Lexer("'multi\nline',")) == ['multiline', ',']


def test_lexer_empty_string():
    assert list(p21.Lexer("'',")) == ['', ',']
    assert list(p21.Lexer("'''',")) == ["'", ',']


def test_lexer_binary():
    # Binary is always a parameter and therefor requires an following terminator ',' or ')'
    assert list(p21.Lexer('"0F", "1FF",')) == [15, ',', 255, ',']
    assert type(list(p21.Lexer('"0F",'))[0]) is int


def test_lexer_binary_error():
    with pytest.raises(p21.ParseError):
        list(p21.Lexer('"",'))
    with pytest.raises(p21.ParseError):
        list(p21.Lexer('"0F,'))
    with pytest.raises(p21.ParseError):
        list(p21.Lexer('"FF",'))


def test_lexer_number():
    # Number is always a parameter and therefor requires an following terminator ',' or ')'
    assert list(p21.Lexer('0, -1, +2, -0.5, +9.3,'))[::2] == [0, -1, 2, -0.5, 9.3]
    assert list(p21.Lexer('1e10, +1E-2, 1.5e-2, 1.6e+10,'))[::2] == [1e10, 1e-2, 1.5e-2, 1.6e+10]
    assert list(p21.Lexer('(1,2,3.5)')) == ['(', 1, ',', 2, ',', 3.5, ')']
    assert type(list(p21.Lexer('0,'))[0]) is int
    assert type(list(p21.Lexer('0.0,'))[0]) is float


def test_lexer_number_error():
    with pytest.raises(p21.ParseError):
        list(p21.Lexer('1a,'))
    with pytest.raises(p21.ParseError):
        list(p21.Lexer('1.5a,'))
    with pytest.raises(p21.ParseError):
        list(p21.Lexer('1e10a,'))
    with pytest.raises(p21.ParseError):
        list(p21.Lexer('1.5e0.5,'))
    with pytest.raises(p21.ParseError):
        list(p21.Lexer('1.5e+0.5,'))


def test_lexer_enum():
    # Enumeration is always a parameter and therefor requires an following terminator ',' or ')'
    assert list(p21.Lexer('.TRUE., .A1., .B_2., .__X__.,'))[::2] == ['.TRUE.', '.A1.', '.B_2.', '.__X__.']
    assert type(list(p21.Lexer('.TRUE.,'))[0]) is p21.Enumeration


def test_lexer_enum_error():
    with pytest.raises(p21.ParseError):
        list(p21.Lexer('.FALSE, '))
    with pytest.raises(p21.ParseError):
        list(p21.Lexer('.0A., '))
    with pytest.raises(p21.ParseError):
        list(p21.Lexer('.., '))
    with pytest.raises(p21.ParseError):
        list(p21.Lexer('.enum.,'))


def test_lexer_keyword():
    assert list(p21.Lexer('KEYWORD() X0KEY _KEY')) == ['KEYWORD', '(', ')', 'X0KEY', '_KEY']
    # allow lowercase keywords, not according to the STEP standard
    assert list(p21.Lexer('Keyword_() X0Key')) == ['Keyword_', '(', ')', 'X0Key']
    assert list(p21.Lexer('!Keyword_() !X0Key')) == ['!Keyword_', '(', ')', '!X0Key']
    # leading number in front of keywords should raise an error in parser
    with pytest.raises(p21.ParseError):
        list(p21.Lexer('0Keyword'))
    # allow '-' to match ISO-10303-21 this is not not a valid keyword!, and should raise a Error in the Parser
    assert list(p21.Lexer('ISO-10303-21;')) == ['ISO-10303-21', ';']
    assert type(list(p21.Lexer('KEYWORD'))[0]) is p21.Keyword
    assert type(list(p21.Lexer('!KEYWORD'))[0]) is p21.UserKeyword
    assert isinstance(list(p21.Lexer('!KEYWORD'))[0], p21.Keyword)


def test_lexer_keyword_error():
    with pytest.raises(p21.ParseError):
        list(p21.Lexer('kEYWORD'))
    with pytest.raises(p21.ParseError):
        list(p21.Lexer('KEY -EYWORD'))


def test_lexer_reference():
    assert list(p21.Lexer('#100=KEY')) == ['#100', '=', 'KEY']


def test_lexer_reference_error():
    with pytest.raises(p21.ParseError):
        list(p21.Lexer('#100a'))
    with pytest.raises(p21.ParseError):
        list(p21.Lexer('#a'))


def test_keyword_matcher():
    from steputils.p21 import KEYWORD
    assert KEYWORD.fullmatch('KEYWORD') is not None
    assert KEYWORD.fullmatch('0KEYWORD') is None
    assert KEYWORD.fullmatch('ISO-10303-21') is None


if __name__ == '__main__':
    pytest.main([__file__])
