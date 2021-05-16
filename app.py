import functools

import flask

import lib2

app = flask.Flask(__name__)
phonemizers = {}


@app.route("/")
def web_index():
    return flask.render_template("index.html")


@functools.lru_cache
def get_phonemizer(l, r):
    return lib2.Phonemizer(language=l, special_rules=lib2.RULES[r])


@app.route("/q")
def web_view():
    s = flask.request.args.get("s", "No data")
    l = flask.request.args.get("l", "en")
    r = flask.request.args.get("r", "none")
    a = flask.request.args.get("a", "true") == "true"
    phonemizer = get_phonemizer(l, r)
    return flask.render_template("view.html", paragraphs=phonemizer.process_text(s, a))
