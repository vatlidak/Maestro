import sys
import ply.yacc as yacc
import pipeline.semantic_analysis as sa
import pipeline.translation as t

# Get the token map from the lexer
from mlex import tokens
precedence = (
    ('left', 'ASSIGN'),
    ('left', 'ADDOP', 'DEP', 'SOFTPDEP', 'SOFTNDEP'),
    ('left', 'MULOP', 'NODEP', 'SOFTNODEP'),
)

lines = 0


def p_program(p):
    'PRGM : STMTLIST'
    line = p.lineno(1)
    node = Node('prgm', [p[1].node], line=line)
    p[0] = AST_obj(node)


def p_stmt_list(p):
    '''STMTLIST : STMTLIST STMT
                | STMT'''
    line = p.lineno(1)
    if len(p) == 2:
        node = Node('stmt-list', [p[1].node], line=line)
    else:
        node = Node('stmt-list', [p[1].node, p[2].node], line=line)
    p[0] = AST_obj(node)


def p_stmt(p):
    '''STMT : E SC
            | SC'''
    p[0] = p[1]


def p_stmt_error(p):
    'STMT : error'
    #line = p.lineno(0) # line number of error
    #print "Syntax error in statement line " + str(line)


def p_stmt_block(p):
    'STMTBLOCK : LC STMTLIST RC'
    p[0] = p[2]


def p_list_loop(p):
    'STMT : E EACH LP ID RP STMTBLOCK'
    line = p.lineno(1)
    _type = 'list'
    id_node = Node('id', [], 'mut', value=p[4], leaf=True, line=line)
    node = Node('list-loop', [p[1].node, id_node, p[6].node], _type, line=line)
    p[0] = AST_obj(node)


# LII is a comma separated list of Expressions
def p_func_call(p):
    'E : ID LP LII RP'
    line = p.lineno(1)
    _type = type_for_func(p[1])
    node = Node(p[1], [p[3].node], _type, line=line)
    p[0] = AST_obj(node)


def p_func_call_error(p):
    'E : ID LP error RP'
    line = p.lineno(1)  # line number of error
    print "Syntax error in function call, line ", line


# assign a variable:
# - put the name in the sym_table
# - the expresion gets the value for 1 liners
def p_assign(p):
    'E : ID ASSIGN E'
    line = p.lineno(1)
    _type = p[3].node._type
    sym_table[p[1]] = [None, _type]
    node = Node('=', [p[1], p[3].node], _type, line=line)
    p[0] = AST_obj(node)


# strings for Job names
def p_e_str(p):
    'E : STR'
    line = p.lineno(1)
    _type = 'string'
    node = Node('str', [], _type, value=str(p[1][1:-1]), leaf=True, line=line)
    p[0] = AST_obj(node)


def p_e_int(p):
    'E : INT'
    line = p.lineno(1)
    _type = 'int'
    node = Node('int', [], _type, value=int(p[1]), leaf=True, line=line)
    p[0] = AST_obj(node)


def p_math_op(p):
    '''E : E MULOP E
         | E ADDOP E'''
    line = p.lineno(1)
    _type = type_for_op(p[1].node._type, p[3].node._type, p[2])
    if _type == None:
        line = p.lineno(2)
        print "Wrong type for mathematical operator in line " + str(line)
        raise SyntaxError
    node = Node(p[2], [p[1].node, p[3].node], _type, line=line)
    p[0] = AST_obj(node)


# lists
def p_e_list(p):
    'E : LI'
    p[0] = p[1]


def p_list(p):
    'LI : LB LII RB'
    p[0] = p[2]
    line = p.lineno(1)
    _type = 'list'
    node = Node('list', [p[2].node], _type, line=line)
    p[0] = AST_obj(node)


# arguments of a function or inside of a list for later
def p_list_inside_grow(p):
    'LII : LII COMMA E'
    _type = 'list'
    line = p.lineno(1)
    node = Node('list-concat', [p[1].node, p[3].node], _type, line=line)
    p[0] = AST_obj(node)


def p_list_inside_orig(p):
    'LII : E'
    _type = 'list'
    line = p.lineno(1)
    node = Node('list-orig', [p[1].node], _type, line=line)
    p[0] = AST_obj(node)


# <->
def p_e_nodep(p):
    'E : E NODEP E'
    line = p.lineno(2)
    _type = 'list'
    node = Node('<->', [p[1].node, p[3].node], _type, line=line)
    p[0] = AST_obj(node)


# ->
def p_e_dep(p):
    'E : E DEP E'
    _type = 'list'
    line = p.lineno(2)
    node = Node('->', [p[1].node, p[3].node], _type, line=line)
    p[0] = AST_obj(node)


# ~>
def p_e_softpdep(p):
    'E : E SOFTPDEP E'
    _type = 'list'
    line = p.lineno(2)
    node = Node('~>', [p[1].node, p[3].node], _type, line=line)
    p[0] = AST_obj(node)


# ~>
def p_e_softndep(p):
    'E : E SOFTNDEP E'
    _type = 'list'
    line = p.lineno(2)
    node = Node('~<', [p[1].node, p[3].node], _type, line=line)
    p[0] = AST_obj(node)


# <~>
def p_e_softnodep(p):
    'E : E SOFTNODEP E'
    _type = 'list'
    line = p.lineno(2)
    node = Node('<~>', [p[1].node, p[3].node], _type, line=line)
    p[0] = AST_obj(node)


# ()
def p_e_parenthesize(p):
    'E : LP E RP'
    p[0] = p[2]


# that's a variable: fetch it in the symbol table
def p_e_id(p):
    'E : ID'
    line = p.lineno(1)
    try:
        _type = sym_table[p[1]][-1]
    except:
        print "Undefined variable " + p[1] + " at line " + str(line)
        raise SyntaxError
    node = Node('id', [], _type, value=p[1], leaf=True, line=line)
    p[0] = AST_obj(node)


# Error rule for syntax errors
def p_error(p):
    print "Syntax error in input: " + str(p)


#type helpers
def type_for_func(name):
    if name == 'Job' or name == 'Wait':
        return 'job'
    elif name in ['run', 'range', 'map', 'reduce']:
        return 'list'


def type_for_op(type1, type2, op):
    if type1 == "job" or type2 == "job":
        print "No mathematic operations for type jobs"
        return None
    if op == '+':
        return type_for_sum(type1, type2)
    elif type1 == type2 == 'int':
        return type1
    else:
        return None
#        raise SyntaxError


def type_for_sum(type1, type2):
    if (type1 == 'int' and type2 == 'string') \
            or (type2 == 'int' and type1 == 'string'):
        return 'string'
    if type1 == type2 == 'int':
        return type1
    return None
#    raise SyntaxError

# Symbol table
sym_table = {}  # map[symbol][value, type]


# AST node structure
class Node:
    def __init__(self, operation, children=None,  \
                       _type=None, value=None, leaf=False, line=-1):
        self._type = _type
        self.operation = operation
        if children:
            self.children = children
        else:
            self.children = []
        self.leaf = leaf
        self.value = value
        self.line = line


# we add one layer of abstraction to be able to get values and syblings
# on top of node
class AST_obj:
    def __init__(self, node=None, value=None, syblings=None):
        self.node = node
        self.syblings = syblings

# Build the parser
parser = yacc.yacc()


# pipeline for execution
def pipeline(code):
    try:
        astree = parser.parse(code)
        if astree == None:
            return None
        ast = astree.node
    except:
        return None
    #sa.traverse(ast)
    sem = sa.analyse(ast)
    if sem == None:
        return "Semantic error. See above!"
    result = t.execute(ast, sym_table)
    # return result
