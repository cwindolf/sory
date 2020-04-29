from typing import NamedTuple, Union, Iterable, List
import re


# -- lexer


class Pound(NamedTuple):
    lit = "#"
    num: int


class Fence(NamedTuple):
    lit = "```"
    annot: str


class Backtick(NamedTuple):
    lit = "`"


class Star(NamedTuple):
    lit = "*"


class Underscore(NamedTuple):
    lit = "_"


class Checkedbox(NamedTuple):
    lit = " [x] "


class Uncheckedbox(NamedTuple):
    lit = " [ ] "


class Bullet(NamedTuple):
    lit = " - "


class Indent(NamedTuple):
    lit = "    "


class Word(NamedTuple):
    word: str


class Blank(NamedTuple):
    lit = " "


class Newline(NamedTuple):
    pass


word_boundary = re.compile(f"[\s{Star.lit}{Underscore.lit}{Backtick.lit}]")


Lex = Union[
    Pound,
    Fence,
    Backtick,
    Star,
    Underscore,
    Checkedbox,
    Uncheckedbox,
    Bullet,
    Indent,
    Word,
    Blank,
    Newline,
]


def lex(lines: Iterable[str]) -> Iterable[Lex]:
    for line in lines:
        # -- things that can only be in the beginning of the line
        while line.startswith(Indent.lit):
            yield Indent()
            line = line[len(Indent.lit):]

        while line.startswith(Pound.lit):
            yield Pound()
            line = line[len(Pound.lit):]

        # this guy consumes the whole line
        while line.startswith(Fence.lit):
            yield Fence(line[len(Fence.lit):])
            line = ""

        # list types come after indent, and only
        # one of these should be parsed as such
        for list_class in (Bullet, Checkedbox, Uncheckedbox):
            if line.startswith(list_class.lit):
                yield list_class()
                line = line[len(list_class.lit):]
                break

        # -- things that occupy the rest of the line
        while line:
            # span delims
            for span_class in (Backtick, Star, Underscore):
                if line.startswith(span_class.lit):
                    yield span_class()
                    line = line[len(span_class.lit):]

            # lowest precedence is taken by blanks and words
            # one blank per space, words are delimited by blanks
            # and span delimiters per `word_boundary` regex
            stripped = line.lstrip()
            if line == stripped:
                match = word_boundary.search(line)
                if match:
                    yield Word(line[: match.start])
                    line = line[match.start:]
                else:
                    yield Word(line)
                    line = ""
            else:
                yield Blank()
                line = line[1:]

        # and of course, signal line end when done with the line
        yield Newline()


# -- parser


class PlainSpan(NamedTuple):
    span: str


class BoldSpan(NamedTuple):
    span: str


class ItalicSpan(NamedTuple):
    span: str


class CodeSpan(NamedTuple):
    span: str


Span = Union[PlainSpan, BoldSpan, ItalicSpan, CodeSpan]


class Text(NamedTuple):
    spans: List[Span]


class LiteralLine(NamedTuple):
    content: str


class CodeBlock(NamedTuple):
    lang: str
    code: List[LiteralLine]


class Quoted(NamedTuple):
    text: Text


Block = Union[Text, CodeBlock, Quoted]


class Check(NamedTuple):
    checked: bool
    stuff: List[Block]


class Checklist(NamedTuple):
    items: List[Check]


class Bullet(NamedTuple):
    stuff: List[Block]


class BulletList(NamedTuple):
    items: List[Bullet]


class Header(NamedTuple):
    level: int
    text: Text


Top = Union[Text, Checklist, BulletList, Header, CodeBlock]


def parse_codespan(lexes: Iterable[Lex], indent: int = 0) -> CodeSpan:
    span = ""

    for cur in lexes:
        if isinstance(cur, Backtick):
            break

        elif isinstance(cur, Word):
            span.append(cur.word)

        elif isinstance(cur, Newline):
            # consume expected indentation
            for i in range(indent):
                assert isinstance(cur, Indent)
                cur = next(lexes)

        else:
            span.append(cur.lit)
    else:
        # we should have seen a Backtick by now
        assert False

    return CodeSpan(span)


def parse_text(cur: Lex, lexes: Iterable[Lex], indent: int = 0) -> Text:
    spans = []
    prev = Newline()
    while not isinstance(prev, Newline) and isinstance(cur, Newline):
        # -- beginning of line stuff
        if isinstance(prev, Newline):
            # consume expected indentation
            for i in range(indent):
                assert isinstance(cur, Indent)
                prev = cur
                cur = next(lexes)

            # consume blanks at the beginning of the line
            while isinstance(cur, Blank):
                prev = cur
                cur = next(lexes)

            # if the line was composed entirely of Indent and
            # Blank, let's call it an empty line and finish
            if isinstance(cur, Newline):
                return spans

        # -- let's parse these spans
        elif isinstance(cur, Backtick):
            spans.append(parse_codespan(lexes, indent=indent))

    return spans


def parse_literalline(
    cur: Lex, lexes: Iterable[Lex], indent: int = 0
) -> LiteralLine:
    # consume expected indentation
    for i in range(indent):
        assert isinstance(cur, Indent)
        cur = next(lexes)

    # store rest of line as literal
    line = ""
    while not isinstance(cur, Newline):
        if isinstance(cur, Word):
            line.append(cur.word)
        else:
            line.append(cur.lit)
        cur = next(lexes)
    assert isinstance(cur, Newline)

    return LiteralLine(line)


def parse_codeblock(
    cur: Lex, lexes: Iterable[Lex], indent: int = 0
) -> CodeBlock:
    # language will be starting fence's annot
    assert isinstance(cur, Fence)
    lang = cur.annot

    # get the actual code as literal lines
    cur = next(lexes)
    code = []
    while not isinstance(cur, Fence):
        code.append(parse_literalline(cur, lexes, indent=indent))
        cur = next(lexes)

    # the literal lines should leave a
    # blank fence at the end
    assert isinstance(cur, Fence)
    assert not cur.annot

    return CodeBlock(lang, code)


def parse_quote(cur: Lex, lexes: Iterable[Lex], indent: int = 0) -> Quoted:
    assert isinstance(cur, Indent)
    return Quoted(parse_text(cur, lexes, indent=indent + 1))


def parse_header(cur: Lex, lexes: Iterable[Lex]) -> Header:
    assert isinstance(cur, Pound)
    level = 1
    cur = next(lexes)
    while isinstance(cur, Pound):
        level += 1
        cur = next(lexes)
    return Header(level, parse_text(cur, lexes))


def parse(lexes: Iterable[Lex]) -> Iterable[Top]:
    for cur in lexes:
        if isinstance(cur, Pound):
            yield parse_header(cur, lexes)

        elif isinstance(cur, Fence):
            yield parse_codeblock(cur, lexes)

        else:
            assert False
