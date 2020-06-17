
#%%
from pyparsing import *
import pyparsing
pyparsing.ParserElement.enablePackrat()

#%%
def parse(raw):

    identifier = Forward()
    expression = Forward()
    functionCall = Forward()
    set = Forward()
    vartype = Forward()

    # General single stuff
    varmat = Combine(Word(alphanums) + ZeroOrMore("_" + Word(alphanums)))
    identifier << Combine(varmat + ZeroOrMore(oneOf(["::", "."]) + varmat))
    literal = (Optional(Literal("f")) + quotedString) ^ pyparsing_common.number

    #MiniStructs
    generics = Combine(Literal("<") + OneOrMore(Combine(vartype + Optional(Literal(", ")))) + Literal(">"))
    vartype << Group(Combine(identifier + Optional(generics)) + Group(ZeroOrMore(Literal("[") + Optional(literal) + Literal("]"))))
    mathOPprio = oneOf([
        "/", "*",
    ])
    mathOP = oneOf([
        "+", "-", "%", "+=", "-="
    ])
    boolOP = oneOf([
        "&&", "||"
    ])
    notOP = oneOf([
        "!"#, "not"
    ])
    shiftOP = oneOf([
        "<<", ">>"
    ])
    compareOP = oneOf([
        "==", ">", "<", "<=", ">=", "!=", "?", #":"
    ])
    #op = mathOPprio ^ mathOP ^ compareOP
    arrIndex = Combine(identifier + ZeroOrMore(Literal("[") + Optional(expression) + Optional(":") + Optional(Literal("]"))))

    # Expressions and calls etc
    set << Literal("{") + delimitedList(expression, delim=",") + Literal("}")
    value = literal ^ identifier ^ Group(functionCall) ^ set ^ arrIndex
    expression << Group(infixNotation(value, [
        (oneOf(':'), 2, opAssoc.LEFT),
        (mathOPprio, 2, opAssoc.LEFT),
        (mathOP, 2, opAssoc.LEFT),
        (notOP, 1, opAssoc.RIGHT),
        (boolOP, 2, opAssoc.LEFT),
        (shiftOP, 2, opAssoc.LEFT),
        (Literal("->"), 2, opAssoc.LEFT),
        (Literal("<-"), 2, opAssoc.RIGHT),
        (compareOP, 2, opAssoc.LEFT),
    ]))
    arguments = ZeroOrMore(delimitedList(expression))
    
    # Statements
    include_statement = Combine(Literal("#include") + Optional(" ") + Optional("<") + Word(alphanums) + Optional(">"))

    return_statement = Keyword ("return") + arguments
    delete_statement = Keyword ("delete") + expression
    break_statement = Keyword ("break")
    lock_statement = Keyword ("lock")
    unlock_statement = Keyword ("unlock")
    #wait_statement = Keyword ("")

    pge_statement = Keyword ("using") + Keyword("olcPixelGameEngine")

    # Variables
    variableTyped = identifier + Literal(":").suppress() + vartype
    variableAssign = (Literal("=").suppress() + Group(ZeroOrMore(delimitedList(expression)))) ^ (Literal("(").suppress() + Group(ZeroOrMore(delimitedList(expression))) + Literal(")").suppress())

    #types
    typeDeclare = Combine(Literal("type") + Optional(generics)) + \
        identifier + Literal(":").suppress()
    contrDestr = oneOf(["make", "drop"]) + \
        Optional(Literal("(").suppress() + Group(ZeroOrMore(Group(variableTyped)))\
        + Literal(")").suppress()) + Literal(":").suppress()

    #methods
    methodDecl = Literal(":").suppress() + \
        vartype + identifier + Group(ZeroOrMore(Literal("(").suppress() + \
        Group(variableTyped) + Literal(")").suppress())) + Literal(":").suppress()

    # Functions & routines and threads
    functionDeclare = Combine(Literal("func") + Optional(generics)) + methodDecl
    routineDeclare = Combine(Literal("routine") + Optional(generics)) + methodDecl
    threadDeclare = Combine(Literal("thread") + Optional(generics)) + methodDecl
    functionCall << identifier + Literal("(").suppress() + Group(arguments) + Literal(")").suppress()
    routineCall = variableTyped + Literal("=").suppress() + Literal("watch") + functionCall
    threadCall = variableTyped + Literal("=").suppress() + Literal("start") + functionCall
    waitforStatement = Literal("waitfor") + identifier
    detachThread = Literal("detach") + identifier
    showStatement = Literal("->") + expression

    # Logic
        # Ifs
    if_statement = Literal("if") + expression + Literal(":").suppress()
    elif_statement = Literal("elif") + expression + Literal(":").suppress()
    else_statement = Literal("else") + Literal(":").suppress()
    ternary_statement = if_statement ^ elif_statement ^ else_statement
        #Whiles
    while_statement = Literal("while") + expression + Literal(":").suppress()
        #Fors
    for_keywords = Literal("in") ^ Literal("of") ^ Literal("to")
    for_statement = Literal("for") + Group(identifier + ZeroOrMore(Literal(",").suppress()+identifier)) + \
        for_keywords + expression + Literal(":").suppress()

    logical_statement = ternary_statement ^ while_statement ^ for_statement

    # Bigger structs
    variableDeclare = identifier + Literal(":").suppress() + vartype
    variableDeclare.setParseAction(lambda wierd_stuff, cool_stuff: ["decl", *cool_stuff])
    assignment = variableTyped + variableAssign
    reassignment = identifier + (Literal("=") + expression)

    # Line
    codeline = Group(ZeroOrMore(Literal("°")) + 
        Optional(Group(variableDeclare ^ routineCall ^ threadCall ^ detachThread ^ waitforStatement ^ assignment ^ functionCall ^ reassignment ^ functionDeclare ^ \
        routineDeclare ^ typeDeclare ^ return_statement ^ break_statement ^ logical_statement ^ expression ^ \
        include_statement ^ delete_statement ^ contrDestr ^ showStatement ^ lock_statement ^ unlock_statement\
        ^ pge_statement ^ threadDeclare)))

    # Blocks

    # Whole Program
    program = delimitedList(codeline ^ "", delim=';')

    return program.parseString(raw)

# %%
