
#%%
import pyparsing
import re

#%%
def writeFromTree(tree):
    return "\n#include <iostream>\n#include <stdlib.h>\n#include <string>\n#include <vector>\n#include <typeinfo>\n#include <thread>\n#include <mutex>\n#include <chrono>\n#include <unistd.h>\nusing namespace std::chrono_literals;\n" + writeHere(tree, customs={
        "functions": {
            "print": {
                "args": "",
                "type": "void",
                "code": 
"""
void print(auto x){
    std::cout << x << std::endl;
}
"""
            },
            "input": {
                "args": "",
                "type": "std::string",
                "code":
"""
std::string input(){
    std::string s;
    std::getline(std::cin, s);
    return s;
}
"""
            },
            "__uni__arrow": {
                "args": "auto* x, auto y",
                "type": "auto",
                "code":
"""
std::string __uni__arrow(std::string* target, std::string object, bool dir) {
    if (dir)
        *target =  object + *target;
    else
        *target += object;
    return *target;
}
int __uni__arrow(int* target, int object, bool dir) {return *target += object;}
std::string __uni__arrow(std::string* target, int object, bool dir) {
    if (dir)
        *target = std::to_string(object) + *target;
    else
        *target += std::to_string(object);
    return *target;
}
""",            "active": True,
            }
        },
        "olcpge": {
            "code": 
"""
#define OLC_PGE_APPLICATION
#include "olcPixelGameEngine.h"
class App : public olc::PixelGameEngine
{
public:
	App(std::string name)
	{
		sAppName = name;
	}

public:
	bool OnUserCreate() override;

	bool OnUserUpdate(float fElapsedTime) override;
};

""",
            },
    }, objects={"functions": {}, "routines": {}, "threads": {}, "mutexes": {}, "variables": {}})

#%%
def writeHere(tree, customs = {}, objects = {}, indent=0):

    outcode = ""

    currentIndent = indent

    for i, codeline in enumerate(tree):

        if len(codeline) == 0:
            continue

        line = codeline[-1]
        currentIndent = len(codeline)-1

        if currentIndent > indent:
            continue

        if currentIndent < indent:
            return outcode

        if line == "°":
            continue

        outcode += "\n" + "\t" * currentIndent


        #single expression
        if len(line) == 1 and line[0] not in ["break", "else", "make", "drop"]\
        and line[0][0] not in ["lock", "unlock"]:
            outcode += f"{eval_expr(line[0], objects)};"

        elif line[0] == 'using' and line[1].lower() == 'olcpixelgameengine':
            customs["olcpge"]["active"] = True

        #routine keywords
        elif line[0] == "waitfor":
            _, idf = line
            outcode += f"__{idf}.join();"
        elif line[0] == "detach":
            _, idf = line
            outcode += f"__{idf}.detach();"
        elif line[0][0] == "lock":
            outcode += f"Mutexes::__{objects['current_exec_space']}_mutex.lock();"
        elif line[0][0] == "unlock":
            outcode += f"Mutexes::__{objects['current_exec_space']}_mutex.unlock();"

        #types
        elif line[0][:4] == "type":
            new_objects = objects
            new_objects["type"] = line[1]
            if len(line[0]) > 4 and "<" in line[0]:
                outcode += f"template <{''.join([f'typename {t}, ' for t in line[0][5:-1].split(', ')])[:-2]}>"\
                    + "\n" + "\t" * currentIndent
            outcode += f"class {line[1]}{{" + \
                writeHere(tree[i+1:], customs, new_objects, currentIndent+1) + \
                    "\n" + "\t" * currentIndent + "}" 
        elif line[0] in ["make", "drop"]:
            prefix = "" if line[0] == "make" else "~"
            if len(line) == 0:
                args = ""
            else:
                args = line[1]
                args = ", ".join([parse_var(arg)[0] for arg in args])
            outcode += f"{prefix}{objects['type']} ({args}){{" + \
                writeHere(tree[i+1:], customs, objects, currentIndent+1) + \
                    "\n" + "\t" * currentIndent + "}" 

        #logic
        elif line[0] in ["if", "while"]:
            _, cond = line
            cond = eval_expr(cond, objects)
            outcode += f"{line[0]} ({cond}){{" + \
                writeHere(tree[i+1:], customs, objects, currentIndent+1) + \
                    "\n" + "\t" * currentIndent + "}"
        elif line[0] == "else":
            outcode += f"else{{" + \
                writeHere(tree[i+1:], customs, objects, currentIndent+1) + \
                    "\n" + "\t" * currentIndent + "}"
        elif line[0] == "for":
            _, indices, keyword, expr = line
            expr = eval_expr(expr, objects)
            
            new_objects = objects
            if keyword == "in":
                for index in indices:
                    new_objects["variables"][index] = "auto"
                outcode += f"for(auto {indices[0]}: {expr}){{" + \
                    writeHere(tree[i+1:], customs, objects, currentIndent+1) + \
                        "\n" + "\t" * currentIndent + "}"
            elif keyword == "of":
                for index in indices:
                    new_objects["variables"][index] = "int"
                idx = indices[0]
                outcode += f"for(int {idx} = 0; {idx} < {expr}.size(); {idx}++){{" + \
                    writeHere(tree[i+1:], customs, objects, currentIndent+1) + \
                        "\n" + "\t" * currentIndent + "}"
            elif keyword == "to":
                for index in indices:
                    new_objects["variables"][index] = "int"
                idx = indices[0]
                outcode += f"for(int {idx} = 0; {idx} < {expr}; {idx}++){{" + \
                    writeHere(tree[i+1:], customs, objects, currentIndent+1) + \
                        "\n" + "\t" * currentIndent + "}"

        elif line[0] == "break":
            outcode += f"break;"

            #show
        elif line[0] == "->":
            _, expr = line
            expr = eval_expr(expr, objects)
            outcode += f"Mutexes::__{objects['current_exec_space']}_mutex.lock();"\
                + "\n" + "\t" * currentIndent + f"*__{objects['current_exec_space']} = {expr};"\
                + "\n" + "\t" * currentIndent + f"Mutexes::__{objects['current_exec_space']}_mutex.unlock();"
        #functions
        elif line[0][:4] == "func":
            if len(line[0]) > 4 and "<" in line[0]:
                outcode += f"template <{''.join([f'typename {t}, ' for t in line[0][5:-1].split(', ')])[:-2]}>"\
                    + "\n" + "\t" * currentIndent
            _, type, name, args = line
            type, dim = parse_type(type)
            type += "*" if len(dim) > 0 else ""
            args = ", ".join([parse_var(arg)[0] for arg in args])
            objects["functions"][name] = {
                "args": args,
                "type": type
            }
            outcode += f"{type} {name}({args}){{" + \
                writeHere(tree[i+1:], customs, objects, currentIndent+1) + \
                    "\n" + "\t" * currentIndent + "}"
        #return
        elif line[0] == "return":
            outcode += f"return {eval_expr(line[1], objects)};"
        #call
        elif len(line) == 2 and isinstance(line[0], str):
            if line[0] not in objects["functions"] and line[0] in customs["functions"]:
                objects["functions"][line[0]] = customs["functions"][line[0]]
                customs["functions"][line[0]]["active"] = True
            outcode += f"{eval_expr(line, objects)};"

        #threads
            #decl
        elif line[0][:7] == "thread":
            if len(line[0]) > 7 and "<" in line[0]:
                outcode += f"template <{''.join([f'typename {t}, ' for t in line[0][5:-1].split(', ')])[:-2]}>"\
                    + "\n" + "\t" * currentIndent
            _, type, name, args = line
            type, dim = parse_type(type)
            type += "*" if len(dim) > 0 else ""
            args = ", ".join([parse_var(arg)[0] for arg in args])
            new_objects = objects
            new_objects["current_exec_space"] = name
            objects["mutexes"][name] = f"\tstd::mutex __{name}_mutex;"
            objects["threads"][name] = {
                "args": args,
                "type": type,
                "code": "\n" + f"void {name}({type}* __{name}, {args}){{" + \
                        writeHere(tree[i+1:], customs, objects, currentIndent+1) + \
                        "\n" + "\t" * currentIndent + "}"
            }
            #call
        elif line[2] == "watch": #rename to start
            observer, type, _, routine, args = line
            var, type = parse_var([observer, type])
            args = ", ".join([str(eval_expr(e, objects)) for e in args])
            outcode += f"{var};" + "\n" + "\t" * currentIndent \
                + f"std::thread {f'__{observer}'}(Threads::{routine}, &{observer}, {args});".replace(", )", ")")
        #routines
            #decl
        elif line[0][:7] == "routine":
            if len(line[0]) > 7 and "<" in line[0]:
                outcode += f"template <{''.join([f'typename {t}, ' for t in line[0][5:-1].split(', ')])[:-2]}>"\
                    + "\n" + "\t" * currentIndent
            _, type, name, args = line
            type, dim = parse_type(type)
            type += "*" if len(dim) > 0 else ""
            args = ", ".join([parse_var(arg)[0] for arg in args])
            new_objects = objects
            new_objects["current_exec_space"] = name
            objects["mutexes"][name] = f"\tstd::mutex __{name}_mutex;"
            objects["routines"][name] = {
                "args": args,
                "type": type,
                "code": "\n" + f"void {name}({type}* __{name}, {args}){{" + \
                        writeHere(tree[i+1:], customs, objects, currentIndent+1) + \
                        "\n" + "\t" * currentIndent + "}"
            }
            #call
        elif line[2] == "watch":
            observer, type, _, routine, args = line
            var, type = parse_var([observer, type])
            args = ", ".join([str(eval_expr(e, objects)) for e in args])
            outcode += f"{var};" + "\n" + "\t" * currentIndent \
                + f"Routines::{routine}(&{observer}, {args});".replace(", )", ")")
        #variables
        elif line[0] == "decl":
            _, name, type = line
            var, type = parse_var([name, type])
            outcode += f"{var};"
            objects["variables"][name] = type
        elif isinstance(line[0], str) and len(line[1]) == 2 and len(line) == 3:
            name, type, values = line
            var, type = parse_var([name, type])
            values = [str(eval_expr(v, objects)) for v in values]
            outcode += f"{var} ({', '.join(values)});"
            objects["variables"][name] = type
        #reassign
        elif line[1] == "=":
            name, _, value = line
            value = eval_expr(value, objects)
            outcode += f"{name} = {value};"


    #fixes
        #Array init
    outcode = re.sub(r'\(({ [a-zA-Z0-9 ,_]* })\)', r'= \1', outcode)
        #Ptrs
    outcode = re.sub(r'ptr<([a-zA-Z0-9_]*)> (\w*) \(new(.*)\)', r'\1* \2 = new \1(\3)', outcode).replace("(, ", "(")
    outcode = re.sub(r'new, ([a-zA-Z])', r'new \1', outcode)
    outcode = re.sub(r'ptr<([a-zA-Z0-9_]*)> (.*) \((.*)\)', r'\1* \2 = &\3', outcode)
    outcode = re.sub(r'ptr<([a-zA-Z0-9_]*)>', r'\1*', outcode)
    outcode = re.sub(r'([a-zA-Z0-9_]*)::value', r'*\1', outcode)
        #casts
    outcode = re.sub(r'([a-zA-Z0-9_]+) : ([a-zA-Z0-9_:]+)', r'static_cast<\2>(\1)', outcode)
    outcode = re.sub(r'<string>', r'<std::string>', outcode)

    #Import customs
    if indent == 0:
        #routines
#        if len(objects["routines"]) > 0:
#            out = ""
#            out += f"\n\nnamespace Routines{{\n"
#            for key in objects["routines"]:
#                out += f"{objects['routines'][key]['code']}\n".replace("\n", "\n\t") \
#                    .replace(", )", ")")[:-1]
#            out += "};\n"
#            outcode = out + "\n" + outcode
        #threads
        if len(objects["threads"]) > 0:
            out = ""
            out += f"\n\nnamespace Threads{{\n"
            for key in objects["threads"]:
                out += f"{objects['threads'][key]['code']}\n".replace("\n", "\n\t") \
                    .replace(", )", ")")[:-1]
            out += "};\n"
            outcode = out + "\n" + outcode
        #mutexes
        if len(objects["mutexes"]) > 0:
            out = ""
            out += f"\n\nnamespace Mutexes{{\n"
            for key in objects["mutexes"]:
                out += f"{objects['mutexes'][key]}\n".replace("\n", "\n\t") \
                    .replace(", )", ")")[:-1]
            out += "};\n"
            outcode = out + "\n" + outcode
        for key in customs["functions"]:
            if key+"(" in outcode:
                customs["functions"][key]["active"] = True
            if "active" in customs["functions"][key]:
                outcode = customs["functions"][key]["code"] + outcode
        if "active" in customs["olcpge"]:
            outcode = customs["olcpge"]["code"] + outcode
    
    print(objects["routines"])

    return outcode


#%%
new_ops = ["<-", "->", "not"]

def eval_expr(expr, scope):
    if str(expr).replace('.', '', 1).replace("-", "").isdigit():
        return expr
    if len(expr) == 0:
        return ""
    if isinstance(expr, str):
        if expr.split("[")[0] in scope["variables"] or expr.split("::")[0]:
            if "[" in expr and ":" in expr.split("[")[1]:
                name = expr.split("[")[0]
                slice = expr.split("[")[1][:-1].split(":")
                first_part, second_part = slice
                type = scope["variables"][name].split("<")[1][:-1]
                return f"std::vector<{type}>({name}.begin()+{first_part}, {name}.begin()+{second_part})"
            return expr
        if expr in ["true", "false", "{", "}"]:
            return expr
        return f"std::string({expr})"
    if len(expr) == 1:
        if isinstance(expr[0], pyparsing.ParseResults):
            return eval_expr(expr[0], scope)
        return eval_expr(expr[0], scope)
    else:
        #function call
        if isinstance(expr[1], pyparsing.ParseResults):
            if expr[0] == "{":
                values = [eval_expr(e, scope) for e in expr[1:-1]]
                return f"{{ {', '.join([str(v) for v in values])} }}"
            return f"{expr[0]}({', '.join([str(eval_expr(e, scope)) for e in expr[1]])})"
        #operation
        elif isinstance(expr[1], str):
            new_expr = expr
            new_expr = process_ops(new_expr, scope)
            new_expr = str(new_expr).replace("[", "(").replace("]", ")")\
                .replace(",", "").replace("'", "").replace(" . ", ".")\
                .replace("|", ",")
            #Make strings good
            new_expr = re.sub('("[a-zA-Z0-9 ]*")', r'std::string(\1)', new_expr)

            #TODO change arrows
            #new_expr = new_expr.replace("<-", "+=").replace("->", "+=")
            return new_expr


def process_ops(expr, scope):

    l = list(expr)

    for op in new_ops:
        temp_list = l
        idx = idx = get_index(temp_list, op)
        while idx == -1 and isinstance(temp_list[0], list):
            temp_list = temp_list[0]
            idx = get_index(temp_list, op)
        while idx != -1:
            left, right = expr[idx-1], expr[idx+1]
            #type_left, type_right = get_type(left, scope), get_type(right, scope)
            if op == "->":
                expr[idx+1] = ""
                expr[idx-1] = ""
                expr[idx] = f"__uni__arrow(&{right}| {left}| true)"
            if op == "<-":
                expr[idx+1] = ""
                expr[idx-1] = ""
                expr[idx] = f"__uni__arrow(&{left}| {right}| false)"

            temp_list = temp_list[idx+1:]
            idx = get_index(temp_list, op)


    return expr

def get_index(arr, val):
    try:
        return arr.index(val)
    except ValueError:
        return -1


def get_type(var, scope):
    if var in scope["variables"]:
        return scope["variables"]["var"]
    elif var.find('"') != -1:
        return "string"
    elif var.isdigit():
        return "int"
    elif var.replace('.', '', 1).isdigit():
        return "double"
    return "int"

# %%
def parse_type(type):
    # Gotta change this
    name, dimensionality = type

    

    if name == "any":
        name = "auto"
    if name == "string":
        name = "std::string"

    dim = "".join([str(d) for d in dimensionality])

    if len(dim) == 2:
        name = f"std::vector<{name}>"
        dim = ""

    return name, dim

def parse_var(var):
    name, type = var
    type, dim = parse_type(type)
    return f"{type} {name}{dim}", type


# %%


# %%
