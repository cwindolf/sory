from typing import NamedTuple, Union, Iterable, List
import itertools
import re


# -- lexer


class Meta(NamedTuple):
    delim = "---"
    meta: dict


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


class Under(NamedTuple):
    lit = "_"


class Checkedbox(NamedTuple):
    lit = " [x] "


class Uncheckedbox(NamedTuple):
    lit = " [ ] "


class Bullet(NamedTuple):
    lit = " - "


class Indent(NamedTuple):
    level: int


class Dedent(NamedTuple):
    pass


class Word(NamedTuple):
    word: str


class Blank(NamedTuple):
    lit = " "


class Newline(NamedTuple):
    pass


# I would rather have these token classes subclass a class
# Lex, but there are big problems mixing inheritance with
# NamedTuple. A union requires bookkeeping but whatever...
Lex = Union[
    Pound,
    Fence,
    Backtick,
    Star,
    Under,
    Checkedbox,
    Uncheckedbox,
    Bullet,
    Indent,
    Dedent,
    Word,
    Blank,
    Newline,
]


# Some helper regexes. Probably most would have more? lol.
whitespace = re.compile("\s")
word_boundary = re.compile(f"[\s{Star.lit}{Under.lit}{Backtick.lit}]")


def lex(lines: Iterable[str]) -> Iterable[Lex]:
    # check first line for indentation
    first_line = next(lines)
    m = whitespace.match(first_line)
    assert not m or m.start

    # meta can only appear at the tippy top of the file
    if first_line.rstrip() == Meta.delim:
        meta = {}
        for line in lines:
            if line.rstrip() == Meta.delim:
                break
            else:
                assert Meta.kv_delim in line
                key, value = line.split(Meta.kv_delim)
                meta[key] = value
        yield Meta(meta)
    else:
        # in the other branch, meta consumes first line
        # so, we only need to put it back if we didn't
        # use it up already.
        lines = itertools.chain([first_line], lines)

    # Python-style indentation stack
    indentation = [0]

    for line in lines:
        # -- things that can only be in the beginning of the line
        # first handle all blank line. it's ignored, it doesn't
        # change the indentation level, etc.
        if not line.strip():
            yield Newline()
            continue

        # deal with indentation: python-style indent / dedent tokens
        # first, see how many blanks the line starts with
        n_spaces = 0
        while not any(
            # ensure that non-Blank tokens that start with
            # whitespace are not eaten by the indentation
            line.startswith(list_class.lit)
            for list_class in (Bullet, Checkedbox, Uncheckedbox)
        ):
            m = whitespace.search(line)
            if m and m.start == 0:
                n_spaces += 1
                line = line[1:]
            else:
                break

        # now get implied indentation from list types,
        # but don't consume the token yet.
        # (no other types require indentation for continuation,
        # they are either delimited like the fence, or just
        # keep rolling like regular text or a header.)
        for list_class in (Bullet, Checkedbox, Uncheckedbox):
            if line.startswith(list_class.lit):
                n_spaces += len(list_class.lit)
                break  # only one list type per line

        # emit the proper {In,De}dents and maintain stack
        if n_spaces > indentation[-1]:
            indentation.append(n_spaces)
            yield Indent(n_spaces)
        elif n_spaces == indentation[-1]:
            pass
        else:
            while n_spaces < indentation[-1]:
                indentation.pop()
                yield Dedent()
        assert indentation[-1] == n_spaces

        # headers
        while line.startswith(Pound.lit):
            assert n_spaces == 0
            yield Pound()
            line = line[len(Pound.lit) :]

        # code block fence
        # this guy consumes the whole line
        while line.startswith(Fence.lit):
            yield Fence(line[len(Fence.lit) :])
            line = ""

        # list types come after indent
        for list_class in (Bullet, Checkedbox, Uncheckedbox):
            if line.startswith(list_class.lit):
                yield list_class()
                line = line[len(list_class.lit) :]
                break  # only one list type per line

        # -- things that occupy the rest of the line
        while line:
            # span delims
            for span_class in (Backtick, Star, Under):
                if line.startswith(span_class.lit):
                    yield span_class()
                    line = line[len(span_class.lit) :]

            # lowest precedence is taken by blanks and words
            # one blank per space, words are delimited by blanks
            # and span delimiters per `word_boundary` regex
            stripped = line.lstrip()
            if line == stripped:
                match = word_boundary.search(line)
                if match:
                    yield Word(line[: match.start])
                    line = line[match.start :]
                else:
                    yield Word(line)
                    line = ""
            else:
                yield Blank()
                line = line[1:]

        # and of course, signal line end when done with the line
        yield Newline()


# -- parser


class Plain(NamedTuple):
    span: str


class Strong(NamedTuple):
    span: str


class Em(NamedTuple):
    span: str


class Code(NamedTuple):
    span: str


Span = Union[Plain, Strong, Em, Code]
DelimitedType = Union[Type[Strong], Type[Em], Type[Code]]


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


def parse_delimited_type(delimited_type: DelimitedType):
    if delimited_type is Strong:
        delimiter_type = Star
    elif delimited_type is Em:
        delimiter_type = Under
    elif delimited_type is Code:
        delimiter_type = Backtick
    else:
        assert False

    def parse_delimited_span(
        lexes: Iterable[Lex], indent: int = 0
    ) -> delimited_type:
        span = ""

        for cur in lexes:
            if isinstance(cur, delimiter_type):
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
            # we should have seen a delimiter by now
            assert False

        return delimited_type(span)

    return parse_delimited_span


# Let's use that factory
parse_code = parse_delimited_type(Code)
parse_em = parse_delimited_type(Em)
parse_strong = parse_delimited_type(Strong)


def parse_text(cur: Lex, lexes: Iterable[Lex], indent: int = 0) -> Text:
    spans = []
    prev = Newline()
    while not (isinstance(prev, Newline) and isinstance(cur, Newline)):
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
            spans.append(parse_code(lexes, indent=indent))
        elif isinstance(cur, Star):
            spans.append(parse_strong(lexes, indent=indent))
        elif isinstance(cur, Under):
            spans.append(parse_em(lexes, indent=indent))

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
