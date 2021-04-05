_base_namespace = {"globals": {key:value for (key, value) in globals().items()}, "locals":{key:value for (key, value) in locals().items()}}
from flask import Flask, render_template, request, jsonify, redirect, url_for
import time, sys, traceback, glob, os, webbrowser
from io import StringIO

_stdin, _stdout, _stderr = sys.stdin, sys.stdout, sys.stderr

app = Flask(__name__)

def get_namespace():
    _globals = {key:value for (key, value) in _base_namespace["globals"].items()}
    _locals = {key:value for (key, value) in _base_namespace["locals"].items()}

    return {"globals":_globals, "locals":_locals}

namespaces = []


def postProcess(data):
    output = "<pre>"
    for l in data:
        if l[-1] == "\n":
            l = l[:-1]
            output += (l + "<br>")
        else:
            output += l

    return output + "</pre>"

@app.route("/")
def home():
    notebooks = [{"name":notebook.split(".mipynb")[-2].split("/")[-1], "link":f"/nb/{notebook}"} for notebook in glob.glob("./*.mipynb")]
    return render_template("home.html", notebooks=notebooks)

@app.route("/nb/<notebook_name>")
def getFile(notebook_name):
    global namespaces
    notebook_name = notebook_name.split(".mipynb")[-2].split("/")[-1]
    if get_index(notebook_name) == -1:
        namespaces.append({"notebook_name": notebook_name, "namespace": get_namespace()})
    try:
        with open(notebook_name+".mipynb") as f:
            data = f.read()
    except FileNotFoundError:
        data = render_template("notebook.html", notebook_name=notebook_name)
        with open(notebook_name+".mipynb", "w") as f:
            f.write(data)
    return data


@app.route("/save", methods=["POST"])
def save():
    head = request.json["head"]
    body = request.json["body"]
    notebook_name = request.json["notebook_name"]

    with open("./" + notebook_name+".mipynb", "w") as f:
        f.write(f"<html><head>{head}</head><body>{body}</body></html>")

    return jsonify({"saved": True})

def get_index(notebook_name):
    for i, namespace in enumerate(namespaces):
        if namespace["notebook_name"] == notebook_name:
            return i
    
    return -1

@app.route("/stop", methods=["POST"])
def stop():
    notebook_name = request.json["notebook_name"]
    ix = get_index(notebook_name)
    if ix != -1:
        namespaces.pop(ix)
    return jsonify({"restarted":True})

@app.route("/del")
def delete():
    nb = request.args.get("nb")
    print(nb)
    if nb:
        os.remove(f"./{nb}.mipynb")
    return jsonify({"deleted":True})

@app.route("/run", methods=["POST"])
def run():
    stdin = StringIO()
    stdout = StringIO()
    stderr = StringIO()

    sys.stdout, sys.stderr, sys.stdin = stdout, stderr, stdin
    
    code = request.json["code"]
    notebook_name = request.json["notebook_name"]
    if get_index(notebook_name) == -1:
        return jsonify({"output":postProcess(["The kernel is stopped or is either crashed. Reload the notebook.\n"]), "error":stderr.read()})
    try:
        exec(code, namespaces[get_index(notebook_name)]["namespace"]["globals"], namespaces[get_index(notebook_name)]["namespace"]["locals"])
    except:
        _type, _value, _tb = sys.exc_info()
        l = len(traceback.extract_tb(_tb))
        traceback.print_exception(_type, _value, _tb, limit=-(l-1))
    
    stdout.seek(0)
    stderr.seek(0)
    sys.stdout, sys.stderr, sys.stdin = _stdout, _stderr, _stdin
    return jsonify({"output":postProcess(stdout.readlines() + stderr.readlines()), "error":stderr.read()})

if __name__ == "__main__":
    webbrowser.open("http://localhost:6060")
    app.run(host="localhost", port=6060)



